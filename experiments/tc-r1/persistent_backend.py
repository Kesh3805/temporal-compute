"""Persistent native worker backend (amendment 0005 section 3a).

Same render(region, begin, end) contract and the same load_batch validation as
the qualified PbrtBatchBackend, but one long-lived PBRT process per stream
serves every request, so launch, parse and acceleration-structure costs are
paid once. Binary and scene provenance are checked at start and at close.
Any protocol, process or validation failure leaves the work unknown and the
instance unusable, as in the qualified bridge.
"""
import hashlib
import json
import os
import queue
import subprocess
import threading
from pathlib import Path

from pbrt_batch_backend import PbrtBatchBackend, load_batch
from progressive_kernel import require

WORKER_SOURCE_SHA256 = '2e0902b75de0a87a498e8a7bcd8a08a1edc4b6be6d98521d2a3660f113262c70'   # v2: adds DUMP
STARTUP_ATTEMPTS = 3
WORKER_SPP = 1 << 30   # sample-index capacity; the independent sampler allocates nothing per spp


class PersistentPbrtBackend(PbrtBatchBackend):
    def __init__(self, binary, build_manifest, scene, scene_sha256, identity, output, threads=1,
                 admitted_scenes=None, timeout=600):
        super().__init__(binary, build_manifest, scene, scene_sha256, identity, output, threads, admitted_scenes)
        manifest = json.loads(Path(build_manifest).read_text(encoding='utf-8'))
        require(manifest.get('worker_source_sha256') == WORKER_SOURCE_SHA256, 'unqualified worker instrumentation')
        self._timeout = timeout
        env = {k: v for k, v in os.environ.items() if not k.startswith('TC_R1')}
        env['TC_R1W_WORKER'] = '1'
        self.command = self._command()
        # A worker that dies before READY has rendered no sample, so a bounded,
        # recorded restart leaves no uncertain work. After READY there is no retry.
        self.startup_failures = []
        for attempt in range(STARTUP_ATTEMPTS):
            self._proc = subprocess.Popen(self.command, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, text=True, bufsize=1)
            self._lines = queue.Queue()
            self._stderr = []
            threading.Thread(target=self._pump, daemon=True).start()
            self._drainer = threading.Thread(target=self._drain, daemon=True)
            self._drainer.start()
            try:
                self._expect('TCR1W READY')
                break
            except RuntimeError as error:
                if self._proc.poll() is None:
                    self._proc.kill()
                    self._proc.wait()
                self.startup_failures.append(dict(attempt=attempt, error=str(error)[:2000]))
                if attempt == STARTUP_ATTEMPTS - 1:
                    self._failed = True
                    raise
            except BaseException:
                self._fail()
                raise

    def _command(self):
        return [str(self.binary), '--nthreads', str(self.threads), '--seed', str(self.seed),
                '--spp', str(WORKER_SPP), '--quiet', str(self.scene)]

    def _drain(self):
        # Keep stderr flowing so a chatty renderer cannot block on a full pipe;
        # retain only the tail for diagnostics.
        for line in self._proc.stderr:
            self._stderr.append(line)
            del self._stderr[:-200]

    def _pump(self):
        for line in self._proc.stdout:
            self._lines.put(line.rstrip('\n'))
        self._lines.put(None)

    def _expect(self, wanted):
        while True:
            try:
                line = self._lines.get(timeout=self._timeout)
            except queue.Empty:
                raise RuntimeError('native worker timed out') from None
            if line is None:
                # stdout EOF can precede stderr collection; wait for both before reporting.
                code = self._proc.wait()
                self._drainer.join(timeout=10)
                raise RuntimeError(f'native worker exited with status {code}: '+''.join(self._stderr)[-2000:])
            if line == wanted:
                return
            require(not line.startswith('TCR1W'), 'unexpected native worker reply')

    def _fail(self):
        self._failed = True
        if self._proc.poll() is None:
            self._proc.kill()
            self._proc.wait()

    def render(self, region, begin, end):
        require(not self._failed, 'backend failed; uncertain work cannot be retried')
        require(type(begin) is int and type(end) is int and 0 <= begin < end <= WORKER_SPP, 'invalid sample range')
        prefix = self.output/f'batch-{self._calls:08d}'
        self._calls += 1
        paths = {suffix: prefix.with_suffix(suffix) for suffix in ('.samples.csv', '.events.csv', '.film.csv')}
        require(not any(p.exists() for p in paths.values()) and not prefix.with_suffix('.json').exists(),
                'batch evidence already exists')
        require(all(' ' not in str(p) for p in paths.values()), 'worker paths must not contain spaces')
        metadata = dict(identity=self.identity, full_seed=self.full_seed, pbrt_seed=self.seed, begin=begin, end=end,
                        binary_sha256=self._binary_sha256, scene_sha256=self._scene_sha256,
                        command=self.command, region=(region.x0, region.x1, region.y0, region.y1),
                        mode='persistent-worker', status='started')
        record = prefix.with_suffix('.json')
        record.write_text(json.dumps(metadata, indent=2)+'\n')
        try:
            self._proc.stdin.write(f'{region.x0} {region.x1} {region.y0} {region.y1} {begin} {end} '
                                   f'{paths[".samples.csv"]} {paths[".events.csv"]} {paths[".film.csv"]}\n')
            self._proc.stdin.flush()
            self._expect(f'TCR1W DONE {region.x0} {region.x1} {region.y0} {region.y1} {begin} {end}')
            samples = load_batch(prefix, region, begin, end)
            metadata.update(status='validated', camera_samples=len(samples),
                            charged_rays=sum(s.charged_rays for s in samples))
            record.write_text(json.dumps(metadata, indent=2)+'\n')
            return samples
        except BaseException as error:
            self._fail()
            metadata.update(status='failed', work_known=False, error_type=type(error).__name__, error=str(error))
            record.write_text(json.dumps(metadata, indent=2)+'\n')
            raise

    def dump(self, region, begin, end):
        """Render [begin, end) for the region without per-sample logs; return its Film RGB (exact float32 values)."""
        import numpy as np
        require(not self._failed, 'backend failed; uncertain work cannot be retried')
        require(type(begin) is int and type(end) is int and 0 <= begin < end <= WORKER_SPP, 'invalid sample range')
        path = self.output/f'dump-{self._calls:08d}.csv'
        self._calls += 1
        require(not path.exists() and ' ' not in str(path), 'dump evidence already exists or path has spaces')
        try:
            self._proc.stdin.write(f'DUMP {region.x0} {region.x1} {region.y0} {region.y1} {begin} {end} {path}\n')
            self._proc.stdin.flush()
            self._expect(f'TCR1W DUMPED {region.x0} {region.x1} {region.y0} {region.y1} {begin} {end}')
            raw = path.read_bytes()
            image = np.full((region.y1-region.y0, region.x1-region.x0, 3), np.nan)
            seen = set()
            for row in raw.decode('ascii').splitlines():
                x, y, r, g, b = row.split(',')
                key = (int(x), int(y))
                require(key not in seen and region.x0 <= key[0] < region.x1 and region.y0 <= key[1] < region.y1,
                        'dump pixel identity')
                seen.add(key)
                image[key[1]-region.y0, key[0]-region.x0] = [float(np.float32(v)) for v in (r, g, b)]
            require(len(seen) == region.area and np.isfinite(image).all(), 'incomplete or nonfinite Film dump')
            return image, hashlib.sha256(raw).hexdigest()
        except BaseException:
            self._fail()
            raise

    def close(self):
        """Stop the worker and confirm the binary and scene were unchanged throughout."""
        if self._proc.poll() is None:
            self._proc.stdin.close()
            try:
                self._proc.wait(timeout=self._timeout)
            except subprocess.TimeoutExpired:
                self._fail()
                raise RuntimeError('native worker did not stop') from None
        require(hashlib.sha256(self.binary.read_bytes()).hexdigest() == self._binary_sha256, 'binary changed')
        require(hashlib.sha256(self.scene.read_bytes()).hexdigest() == self._scene_sha256, 'scene changed')
        require(self._proc.returncode == 0 and not self._failed, 'native worker did not finish cleanly')
