"""Small fixed-horizon paired-stream harness, not an experiment runner."""
from copy import deepcopy
from dataclasses import dataclass
import time

from baselines import BATCH_SPP, MINIMUM_SPP, initial_request, validate_observations
from progressive_kernel import ProgressiveKernel, WorkRequest, pbrt_seed_map, require


@dataclass(frozen=True)
class PairedResult:
    production_image: tuple
    allocation_charged_rays: int
    production_charged_rays: int
    elapsed_ns: int
    trace: tuple

    @property
    def charged_rays(self):
        return self.allocation_charged_rays + self.production_charged_rays


class PairedPolicyRunner:
    """Owns fresh kernels. Only allocation snapshots cross choose's boundary.

    Backend identities are provenance declarations, not a process security sandbox.
    Native backends separately verify actual scene/binary/seed admission. Numeric
    synthetic backends permit correctness testing without launching a renderer.
    """
    def __init__(self, width, height, allocation_backend, production_backend,
                 regions=None, clock=time.perf_counter_ns):
        require(allocation_backend is not production_backend, 'shared stream backend')
        identities = tuple(tuple(b.identity) for b in (allocation_backend, production_backend))
        require(all(len(i) == 4 for i in identities), 'invalid stream identity')
        require(identities[0][:3] == identities[1][:3] and
                identities[0][3] == 'allocation' and identities[1][3] == 'production',
                'unpaired stream identities')
        seeds = pbrt_seed_map(identities)
        for backend, identity in zip((allocation_backend, production_backend), identities):
            if hasattr(backend, 'seed'):
                require(backend.seed == seeds[identity][1], 'backend seed mismatch')
        # Native admission verifies these fingerprints; pairing must not silently
        # combine different scenes/binaries/thread settings under equal labels.
        for name in ('_scene_sha256', '_binary_sha256', 'threads'):
            require(hasattr(allocation_backend, name) == hasattr(production_backend, name),
                    'inconsistent native pairing metadata')
            if hasattr(allocation_backend, name):
                require(getattr(allocation_backend, name) == getattr(production_backend, name),
                        'native pairing configuration mismatch')
        self._allocation = ProgressiveKernel(width, height, allocation_backend, regions, clock)
        self._production = ProgressiveKernel(width, height, production_backend,
                                             self._allocation.regions, clock)
        self._clock = clock
        self._trace = []
        self._used = False

    @property
    def trace(self):
        return tuple(deepcopy(self._trace))

    def run(self, policy, decisions):
        require(not self._used, 'paired runner already used; no retry')
        require(type(decisions) is int and decisions >=
                (MINIMUM_SPP // BATCH_SPP) * len(self._allocation.regions),
                'decision horizon cannot complete minimum coverage')
        self._used = True
        record = None
        try:
            started = self._clock()
            for step in range(decisions):
                step_started = self._clock()
                states = validate_observations(self._allocation.observe())
                request = policy.choose(states)
                require(isinstance(request, WorkRequest) and request.region in self._allocation.regions
                        and type(request.additional_samples) is int
                        and request.additional_samples == BATCH_SPP, 'invalid common policy request')
                required = initial_request(states)
                require(required is None or request == required, 'common minimum coverage violated')
                record = dict(step=step, allocation_before=states, request=request,
                              candidates=deepcopy(getattr(policy, 'diagnostics', ())), status='started')
                self._trace.append(record)
                allocation = self._allocation.sample_region(request)
                record['allocation_charged_rays'] = self._allocation.trace[-1]['charged_rays']
                production = self._production.sample_region(request)
                record['production_charged_rays'] = self._production.trace[-1]['charged_rays']
                require(allocation.samples_per_pixel == production.samples_per_pixel,
                        'paired sample count divergence')
                record['allocation_after'] = allocation
                record['production_completion'] = dict(version=production.version,
                        sample_count=production.sample_count,
                        samples_per_pixel=production.samples_per_pixel,
                        charged_rays=production.charged_rays)
                elapsed_step = self._clock() - step_started
                require(type(elapsed_step) is int and elapsed_step > 0, 'invalid decision elapsed time')
                record['elapsed_ns'] = elapsed_step
                record['status'] = 'committed'
            allocation = self._allocation.stop('fixed decision horizon; not registered ray/time cap')
            production = self._production.stop('fixed decision horizon; not registered ray/time cap')
            image = self._production.image()
            elapsed = self._clock() - started
            require(type(elapsed) is int and elapsed > 0, 'invalid paired elapsed time')
            return PairedResult(image, sum(s.charged_rays for s in allocation),
                                sum(s.charged_rays for s in production), elapsed, self.trace)
        except BaseException as error:
            incomplete = record is not None and record['status'] == 'started'
            if incomplete:
                record.update(status='failed', work_known=False,
                              error_type=type(error).__name__, error=str(error))
            self._trace.append(dict(status='failed', error_type=type(error).__name__, error=str(error),
                                    work_known=self._allocation.work_known and self._production.work_known
                                    and not incomplete,
                                    allocation_trace=self._allocation.trace,
                                    production_trace=self._production.trace))
            raise
