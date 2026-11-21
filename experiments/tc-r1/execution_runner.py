"""TC-R1 policy run under amendments 0003-0005 (one unit, one policy, one timing repeat).

Paired allocation/production kernels; both streams charged; policy sees only
allocation observations. Checkpoints are actual initialization charge plus the
registered increments (0003). Production snapshots are taken every 2^20 charged
rays after initialization, and the run continues until both the last
checkpoint is committed and the common wall cap C has elapsed (0005). Snapshot
images go to a caller-supplied sink, scored offline after the run, never fed
back to the policy. Diagnostics stream to a JSON-lines file.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import json
import time

from amended_policies import AmendedConventionalPolicy
from baselines import BATCH_SPP, MINIMUM_SPP, ConventionalPolicy, initial_request, validate_observations
from cached_kernel import CachedProgressiveKernel
from progressive_kernel import WorkRequest, require
from ray_cost import RayCostTcPolicy

POLICIES = ('uniform', 'adaptive-mc-ucb-region', 'variance-guided', 'tc-full', 'tc-equal-cost', 'tc-no-feedback')
INCREMENTS = (2**20, 2**22, 2**24, 2**26)
SNAPSHOT_RAYS = 2**20
AUDIT_PERIOD = 256   # full candidate dumps every 256th decision; all runs replay deterministically


def _values(policy):
    """(region geometry, ranking value) pairs from the policy's last decision, without copying history."""
    if isinstance(policy, RayCostTcPolicy):
        record = policy._diagnostics[-1] if policy._diagnostics else None
        policy._diagnostics.clear()   # the policy never reads its history; it is streamed here instead
        if record is None:
            return None, ()
        return record['reason'], tuple((tuple(c['region']), c['score']) for c in record['candidates'])
    reason = getattr(policy, 'last_reason', None)
    if isinstance(policy, AmendedConventionalPolicy):
        if policy.method != 'variance-guided' or reason != 'index':
            return reason, ()
        policy = policy._variance_guided
    return reason, tuple(((c.region.y0, c.region.x0, c.region.y1, c.region.x1), c.index)
                         for c in policy.diagnostics)


def summarize(policy, step, request):
    """Per-decision trace: chosen region, reason, chosen and best alternative ranking values."""
    reason, values = _values(policy)
    chosen_key = (request.region.y0, request.region.x0, request.region.y1, request.region.x1)
    chosen = [v for k, v in values if k == chosen_key]
    others = sorted((v for k, v in values if k != chosen_key), reverse=True)
    value = dict(step=step, region=asdict(request.region), reason=reason,
                 chosen_value=chosen[0] if chosen else None, runner_up_value=others[0] if others else None)
    if step % AUDIT_PERIOD == 0:
        value['candidates'] = [[list(k), v] for k, v in values]
    return value


def make_policy(name):
    """Registered policies as amended by 0004 (floor, scale-equivariant MC-UCB) and 0005 (ray cost)."""
    require(name in POLICIES, 'unregistered policy')
    if name == 'uniform':
        return ConventionalPolicy('uniform')
    if name in ('adaptive-mc-ucb-region', 'variance-guided'):
        return AmendedConventionalPolicy(name)
    return RayCostTcPolicy(name[len('tc-'):])


class PolicyRun:
    """One policy run. backends(stream) returns a fresh backend for 'allocation' or 'production'."""
    def __init__(self, width, height, backends, cap_seconds, snapshot_sink, diagnostics_path,
                 clock=time.perf_counter, increments=INCREMENTS, snapshot_rays=SNAPSHOT_RAYS):
        # Non-default increments/cadence exist only for synthetic tests; execution binds the registered values.
        require(type(cap_seconds) in (int, float) and cap_seconds > 0, 'positive common wall cap required')
        self.width, self.height = width, height
        self.backends, self.cap, self.sink, self.clock = backends, float(cap_seconds), snapshot_sink, clock
        self.diagnostics_path = diagnostics_path
        require(all(type(v) is int and v > 0 for v in increments) and list(increments) == sorted(set(increments)),
                'increments must be increasing positive ints')
        require(type(snapshot_rays) is int and snapshot_rays > 0 and all(v % snapshot_rays == 0 for v in increments),
                'increments must be multiples of the snapshot cadence')
        self.increments, self.snapshot_rays = tuple(increments), snapshot_rays

    def run(self, policy_name, max_requests=None):
        policy = make_policy(policy_name)
        started = self.clock()
        allocation_backend, production_backend = self.backends('allocation'), self.backends('production')
        allocation = CachedProgressiveKernel(self.width, self.height, allocation_backend)
        production = CachedProgressiveKernel(self.width, self.height, production_backend, allocation.regions)
        record = dict(policy=policy_name, requests=0, checkpoints=[], snapshots=[], initialization=None,
                      status='running')
        pool = ThreadPoolExecutor(max_workers=2)
        try:
            with open(self.diagnostics_path, 'x', encoding='utf-8') as diagnostics:
                thresholds, next_snapshot = None, None
                while True:
                    total = self._charge(allocation, production)
                    elapsed = self.clock() - started
                    finished = thresholds is not None and not thresholds and elapsed >= self.cap
                    if finished or (max_requests is not None and record['requests'] >= max_requests):
                        break
                    states = validate_observations(allocation.observe())
                    request = policy.choose(states)
                    require(isinstance(request, WorkRequest) and request.region in allocation.regions and
                            request.additional_samples == BATCH_SPP, 'invalid common policy request')
                    required = initial_request(states)
                    require(required is None or request == required, 'common minimum coverage violated')
                    diagnostics.write(json.dumps(summarize(policy, record['requests'], request), default=str)+'\n')
                    # Both streams render the same request concurrently; both are charged.
                    futures = [pool.submit(k.sample_region, request) for k in (allocation, production)]
                    after = [f.result() for f in futures]
                    require(after[0].samples_per_pixel == after[1].samples_per_pixel, 'paired sample count divergence')
                    record['requests'] += 1
                    total = self._charge(allocation, production)
                    if thresholds is None and min(s.samples_per_pixel for s in allocation.observe()) >= MINIMUM_SPP:
                        # Mandatory coverage complete on both streams: A_u is the actual charge so far.
                        record['initialization'] = total
                        thresholds = [total + i for i in self.increments]
                        next_snapshot = total + self.snapshot_rays
                    if thresholds is None:
                        continue
                    now = self.clock() - started
                    while next_snapshot is not None and total >= next_snapshot:
                        image = production.image()
                        m = (next_snapshot - record['initialization'])//self.snapshot_rays
                        record['snapshots'].append(dict(index=m, nominal=next_snapshot, actual=total,
                                                        seconds=now, sink=self.sink(policy_name, m, image)))
                        next_snapshot += self.snapshot_rays
                    while thresholds and total >= thresholds[0]:
                        nominal = thresholds.pop(0)
                        record['checkpoints'].append(dict(increment=self.increments[len(record['checkpoints'])],
                                                          nominal=nominal, actual=total, overshoot=total-nominal,
                                                          seconds=now))
            allocation.stop('registered run end: final checkpoint committed and common wall cap reached')
            production.stop('registered run end: final checkpoint committed and common wall cap reached')
            record.update(status='complete', seconds=self.clock() - started, charged_rays=self._charge(allocation,
                                                                                                         production))
            return record
        except BaseException as error:
            record.update(status='failed', work_known=False, error_type=type(error).__name__, error=str(error)[:500])
            raise
        finally:
            pool.shutdown(wait=True)
            for backend in (allocation_backend, production_backend):
                if hasattr(backend, 'close') and not getattr(backend, '_failed', False):
                    backend.close()

    @staticmethod
    def _charge(allocation, production):
        return sum(s.charged_rays for s in allocation.observe()) + sum(s.charged_rays for s in production.observe())
