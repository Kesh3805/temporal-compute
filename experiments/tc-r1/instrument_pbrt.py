"""Minimal CPU qualification instrumentation; does not replace the path kernel."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

PIN = 'b4ce9687e6c695f5582997c61b0c66cf064bdb4a'


def instrument(root):
    revision = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != PIN or subprocess.check_output(['git','-C',str(root),'status','--porcelain'],text=True):
        raise ValueError('expected clean pinned PBRT source')
    path = root/'src/pbrt/cpu/integrators.cpp'
    original = path.read_text(encoding='utf-8')
    source = original

    def replace(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError(f'upstream anchor not unique: {old[:70]}')
        source = source.replace(old,new)

    replace('#include <algorithm>', '#include <algorithm>\n#include <cstdlib>\n#include <fstream>\n#include <iomanip>\n#include <mutex>')
    counters = 'STAT_COUNTER("Intersections/Regular ray intersection tests", nIntersectionTests);\nSTAT_COUNTER("Intersections/Shadow ray intersection tests", nShadowTests);'
    replace(counters,'// Qualification counters declared with camera counter above.')
    replace('STAT_COUNTER("Integrator/Camera rays traced", nCameraRays);',
            'STAT_COUNTER("Integrator/Camera rays traced", nCameraRays);\n'+counters)
    replace('int spp = samplerPrototype.SamplesPerPixel();', '''int spp = samplerPrototype.SamplesPerPixel();
    int qualificationBegin = 0;
    if (const char *v = std::getenv("TC_R1E_SAMPLE_BEGIN")) qualificationBegin = std::stoi(v);
    if (const char *v = std::getenv("TC_R1E_SAMPLE_END")) spp = std::stoi(v);
    if (qualificationBegin < 0 || qualificationBegin >= spp || spp > samplerPrototype.SamplesPerPixel())
        ErrorExit("Invalid qualification sample interval");''')
    replace('int64_t(spp) * pixelBounds.Area()', 'int64_t(spp - qualificationBegin) * pixelBounds.Area()')
    replace('int waveStart = 0, waveEnd = 1, nextWaveSize = 1;',
            'int waveStart = qualificationBegin, waveEnd = qualificationBegin + 1, nextWaveSize = 1;')
    start = source.index('void RayIntegrator::EvaluatePixelSample(')
    body = source.index('{',start)+1
    source = source[:body]+'\n    const int64_t qCamera = nCameraRays, qRegular = nIntersectionTests, qShadow = nShadowTests;'+source[body:]
    replace('// Add camera ray\'s contribution to image', '''// Qualification-only per-sample diagnostic; no kernel/settings changes.
    if (const char *qPath = std::getenv("TC_R1E_SAMPLE_LOG")) {
        static std::mutex qMutex;
        std::lock_guard<std::mutex> guard(qMutex);
        static std::ofstream qLog(qPath);
        if (!qLog) ErrorExit("Cannot write qualification sample log");
        RGB qRGB = camera.GetFilm().ToOutputRGB(L, lambda);
        qLog << pPixel.x << ',' << pPixel.y << ',' << sampleIndex << ','
             << std::setprecision(17) << qRGB.r << ',' << qRGB.g << ',' << qRGB.b << ','
             << nCameraRays-qCamera << ',' << nIntersectionTests-qRegular << ',' << nShadowTests-qShadow << '\\n';
    }
    // Add camera ray's contribution to image''')
    path.write_text(source,encoding='utf-8',newline='\n')
    return dict(upstream_commit=PIN, source_sha256=hashlib.sha256(original.encode()).hexdigest(),
                instrumented_sha256=hashlib.sha256(source.encode()).hexdigest(),
                modified_path='src/pbrt/cpu/integrators.cpp',
                scope='CPU pinhole path with RGB Film ToOutputRGB, no participating media',
                accumulation_limitation='Nonzero sample-begin images use stock film metadata/normalization; only sample records are valid for these batch fixtures.')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    args=parser.parse_args()
    value=instrument(args.source)
    args.manifest.parent.mkdir(parents=True,exist_ok=True)
    args.manifest.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
