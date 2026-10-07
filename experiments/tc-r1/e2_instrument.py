"""Single E2 adapter layered on the preserved E1 instrumentor."""
import argparse
import hashlib
import json
from pathlib import Path

from instrument_pbrt import instrument


def apply(root):
    manifest=instrument(root)
    path=root/'src/pbrt/cpu/integrators.cpp'
    source=path.read_text()

    def replace(old,new):
        nonlocal source
        if source.count(old)!=1:
            raise ValueError('ambiguous E2 instrumentation anchor: '+old[:60])
        source=source.replace(old,new)

    replace('namespace pbrt {', '''namespace pbrt {
static thread_local int e2x, e2y, e2index;
static thread_local int64_t e2total, e2camera, e2continuation, e2visibility;
static void E2Charge(const char *kind) {
    ++e2total;
    if (kind[0] == 'c' && kind[1] == 'a') ++e2camera;
    else if (kind[0] == 'c') ++e2continuation;
    else ++e2visibility;
    if (const char *p = std::getenv("TC_R1E2_EVENTS")) {
        static std::mutex mutex;
        std::lock_guard<std::mutex> lock(mutex);
        static std::ofstream out(p);
        if (!out) ErrorExit("Cannot write E2 events");
        out << e2x << ',' << e2y << ',' << e2index << ',' << kind << '\\n';
    }
}''')
    replace('const int64_t qCamera = nCameraRays, qRegular = nIntersectionTests, qShadow = nShadowTests;',
            '''e2x = pPixel.x; e2y = pPixel.y; e2index = sampleIndex;
    e2total = e2camera = e2continuation = e2visibility = 0;
    const int64_t qCamera = nCameraRays, qRegular = nIntersectionTests, qShadow = nShadowTests;''')
    replace('++nCameraRays;', '++nCameraRays; E2Charge("camera");')
    # Only native PathIntegrator::Li, not other integrators.
    start=source.index('SampledSpectrum PathIntegrator::Li(')
    end=source.index('SampledSpectrum PathIntegrator::SampleLd(',start)
    body=source[start:end]
    anchor='ray = isect.SpawnRay(ray, bsdf, bs->wi, bs->flags, bs->eta);'
    if body.count(anchor)!=1:
        raise ValueError('path continuation anchor changed')
    body=body.replace(anchor,anchor+'\n        E2Charge("continuation");')
    source=source[:start]+body+source[end:]
    replace('++nShadowTests;', '++nShadowTests; E2Charge("visibility");')
    replace("<< nCameraRays-qCamera << ',' << nIntersectionTests-qRegular << ',' << nShadowTests-qShadow << '\\n';",
            "<< nCameraRays-qCamera << ',' << nIntersectionTests-qRegular << ',' << nShadowTests-qShadow << ',' << e2total << ',' << e2camera << ',' << e2continuation << ',' << e2visibility << '\\n';")
    replace('cameraSample.filterWeight);\n}', '''cameraSample.filterWeight);
    if (const char *p = std::getenv("TC_R1E2_FILM")) {
        static std::mutex mutex;
        std::lock_guard<std::mutex> lock(mutex);
        static std::ofstream out(p);
        if (!out) ErrorExit("Cannot write E2 Film values");
        RGB rgb = camera.GetFilm().GetPixelRGB(pPixel);
        out << pPixel.x << ',' << pPixel.y << ',' << sampleIndex << ','
            << std::setprecision(17) << rgb.r << ',' << rgb.g << ',' << rgb.b << '\\n';
    }
}''')
    path.write_text(source,encoding='utf-8',newline='\n')
    manifest['e2_source_sha256']=hashlib.sha256(source.encode()).hexdigest()
    manifest['preregistration']='7f610be4eb137aae85c3fe97721a2a3ae5366ca3'
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    args=parser.parse_args()
    args.manifest.parent.mkdir(parents=True,exist_ok=True)
    args.manifest.write_text(json.dumps(apply(args.source),indent=2)+'\n')
