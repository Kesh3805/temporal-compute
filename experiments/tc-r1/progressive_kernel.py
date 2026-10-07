"""Small synchronous TC-R1 policy boundary; no policies or reference access."""
from dataclasses import dataclass
import hashlib
import math
import time


def require(condition, message):
    if not condition:
        raise ValueError(message)


@dataclass(frozen=True, order=True)
class Region:
    x0: int
    x1: int
    y0: int
    y1: int

    def pixels(self):
        return ((x, y) for y in range(self.y0, self.y1) for x in range(self.x0, self.x1))

    @property
    def area(self):
        return (self.x1-self.x0)*(self.y1-self.y0)


@dataclass(frozen=True)
class WorkRequest:
    region: Region
    additional_samples: int


@dataclass(frozen=True)
class RegionState:
    region: Region
    version: int
    sample_count: int
    samples_per_pixel: int
    mean: tuple | None
    variance: tuple | None
    standard_error: tuple | None
    recent_improvement: float | None
    estimated_sample_cost: float | None
    charged_rays: int


@dataclass(frozen=True)
class NativeSample:
    x: int
    y: int
    index: int
    rgb: tuple
    camera_queries: int
    regular_queries: int
    visibility_queries: int
    camera: int
    continuation: int
    visibility: int

    @property
    def charged_rays(self):
        return self.camera+self.continuation+self.visibility

    def validate(self):
        counts=(self.x,self.y,self.index,self.camera_queries,self.regular_queries,
                self.visibility_queries,self.camera,self.continuation,self.visibility)
        require(all(type(v) is int and v>=0 for v in counts),'invalid native integer')
        require(len(self.rgb)==3 and all(math.isfinite(v) for v in self.rgb),'invalid native RGB')
        require(self.camera_queries==self.camera==1,'camera charge/query mismatch')
        require(self.visibility_queries==self.visibility,'visibility charge/query mismatch')
        require(0<=self.regular_queries-self.camera_queries<=self.continuation,
                'continuation charge/query mismatch')


@dataclass
class Moments:
    count: int = 0
    mean: tuple = (0.,0.,0.)
    m2: tuple = (0.,0.,0.)

    def add(self, rgb):
        n=self.count+1
        delta=tuple(rgb[c]-self.mean[c] for c in range(3))
        mean=tuple(self.mean[c]+delta[c]/n for c in range(3))
        m2=tuple(self.m2[c]+delta[c]*(rgb[c]-mean[c]) for c in range(3))
        require(all(math.isfinite(v) and v>=0 for v in m2),'invalid second moment')
        require(all(math.isfinite(v) for v in mean),'invalid mean')
        self.count,self.mean,self.m2=n,mean,m2


def stream_seed(scene_id, frame_id, replicate, stream):
    require(type(replicate) is int and 0<=replicate<8,'invalid replicate')
    require(stream in ('allocation','production','reference-a','reference-b','timing-order'),
            'invalid stream')
    require(all(isinstance(v,str) and v and '|' not in v for v in (scene_id,frame_id)),
            'invalid stream identifier')
    value=f'tc-r1-v1|20261007|{scene_id}|{frame_id}|{replicate}|{stream}'
    return int.from_bytes(hashlib.sha256(value.encode('utf-8')).digest()[:8],'big')


def pbrt_seed_map(identities):
    result={}
    used=set()
    for identity in identities:
        require(identity not in result,'duplicate stream identity')
        full=stream_seed(*identity)
        projected=full & 0x7fffffff
        require(projected not in used,'projected PBRT seed collision')
        used.add(projected)
        result[identity]=(full,projected)
    return result


class ProgressiveKernel:
    """One frame, one stream, immutable region partition; synchronous requests only.

    Backend.render(region, begin, end) returns complete validated native samples.
    It must independently validate class ledgers/Film and retain its diagnostics.
    This class never truncates a path, selects future indices, or reads references.
    """
    def __init__(self, width, height, backend, regions=None, clock=time.perf_counter_ns):
        require(type(width) is int and type(height) is int and width>0 and height>0,
                'invalid frame dimensions')
        self.width,self.height=width,height
        if regions is None:
            regions=tuple(Region(x,min(x+16,width),y,min(y+16,height))
                          for y in range(0,height,16) for x in range(0,width,16))
        self.regions=tuple(regions)
        covered=set()
        for region in self.regions:
            require(isinstance(region,Region) and
                    all(type(v) is int for v in (region.x0,region.x1,region.y0,region.y1)) and
                    0<=region.x0<region.x1<=width and 0<=region.y0<region.y1<=height,
                    'invalid region bounds')
            pixels=set(region.pixels())
            require(not covered.intersection(pixels),'overlapping partition')
            covered.update(pixels)
        require(len(covered)==width*height,'partition does not cover frame')
        self._backend,self._clock=backend,clock
        self._moments={p:Moments() for p in covered}
        self._charges={r:0 for r in self.regions}
        self._cost={r:None for r in self.regions}
        self._improvement={r:None for r in self.regions}
        self._version=0
        self._stopped=False
        self._busy=False
        self._failed=False
        self._trace=[]

    @property
    def trace(self):
        return tuple(dict(entry) for entry in self._trace)

    @property
    def work_known(self):
        return not self._failed

    def observe(self):
        states=[]
        for region in self.regions:
            values=[self._moments[p] for p in region.pixels()]
            n=values[0].count
            require(all(v.count==n for v in values),'nonuniform committed region')
            mean=tuple(math.fsum(v.mean[c] for v in values)/region.area for c in range(3)) if n else None
            variance=tuple(math.fsum(v.m2[c]/(n-1) for v in values)/region.area for c in range(3)) if n>1 else None
            stderr=tuple(math.sqrt(math.fsum(v.m2[c]/((n-1)*n) for v in values))/region.area for c in range(3)) if n>1 else None
            states.append(RegionState(region,self._version,n*region.area,n,mean,variance,
                                      stderr,self._improvement[region],self._cost[region],self._charges[region]))
        return tuple(states)

    def sample_region(self, request):
        require(not self._stopped and not self._busy,'kernel stopped or busy')
        require(isinstance(request,WorkRequest) and request.region in self.regions,'unknown region')
        require(type(request.additional_samples) is int and 1<=request.additional_samples<=16,
                'invalid sample increment')
        region=request.region
        before=self.observe()[self.regions.index(region)]
        begin=before.samples_per_pixel
        end=begin+request.additional_samples
        require(end<=0x7fffffff,'native sample index exhausted')
        self._busy=True
        previous_moments={p:self._moments[p] for p in region.pixels()}
        previous=(self._charges[region],self._cost[region],self._improvement[region],self._version)
        try:
            started=self._clock()
            samples=list(self._backend.render(region,begin,end))
            expected={(x,y,i) for x,y in region.pixels() for i in range(begin,end)}
            seen=set()
            for sample in samples:
                require(isinstance(sample,NativeSample),'invalid native sample type')
                sample.validate()
                key=(sample.x,sample.y,sample.index)
                require(key in expected and key not in seen,'wrong or duplicate sample ownership')
                seen.add(key)
            require(seen==expected,'incomplete sample batch')
            # Stage all updates; failed validation cannot expose a partial estimator.
            staged={p:Moments(self._moments[p].count,self._moments[p].mean,self._moments[p].m2)
                    for p in region.pixels()}
            for sample in sorted(samples,key=lambda s:(s.y,s.x,s.index)):
                staged[(sample.x,sample.y)].add(sample.rgb)
            charged=sum(s.charged_rays for s in samples)
            self._moments.update(staged)
            self._charges[region]+=charged
            self._version+=1
            after=self.observe()[self.regions.index(region)]
            improvement=(math.fsum(v*v for v in before.standard_error)-
                         math.fsum(v*v for v in after.standard_error)) if before.standard_error is not None else None
            self._improvement[region]=improvement
            elapsed=self._clock()-started
            require(type(elapsed) is int and elapsed>0,'invalid measured request duration')
            self._cost[region]=elapsed/1e9/len(samples)
            self._trace.append(dict(action='SampleRegion',region=(region.x0,region.x1,region.y0,region.y1),
                                    begin=begin,end=end,version=self._version,charged_rays=charged,
                                    elapsed_ns=elapsed,status='committed'))
            return self.observe()[self.regions.index(region)]
        except Exception as error:
            self._moments.update(previous_moments)
            self._charges[region],self._cost[region],self._improvement[region],self._version=previous
            self._failed=self._stopped=True
            self._trace.append(dict(action='SampleRegion',region=(region.x0,region.x1,region.y0,region.y1),
                                    begin=begin,end=end,status='failed',work_known=False,error=str(error)))
            raise
        finally:
            self._busy=False

    def stop(self, reason):
        require(not self._busy,'kernel busy')
        require(isinstance(reason,str) and bool(reason.strip()),'missing stop reason')
        require(not self._stopped,'kernel already stopped')
        self._stopped=True
        self._trace.append(dict(action='Stop',reason=reason,version=self._version,status='committed'))
        return self.observe()

    def image(self):
        require(self.work_known,'failed kernel cannot supply a scored image')
        require(all(v.count>0 for v in self._moments.values()),'incomplete image coverage')
        return tuple(tuple(self._moments[(x,y)].mean for x in range(self.width)) for y in range(self.height))
