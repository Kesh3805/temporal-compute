"""Amendment 0005 section 3(a): persistent request loop over the unchanged E3 layer.

Applies the qualified e3_instrument.py first, then two changes only:

1. The sample, event and Film logs reopen when their environment path changes
   (previously a function-static ofstream bound on first use). Written bytes are
   unchanged, and a per-request process still opens each log exactly once.
2. When TC_R1W_WORKER is set, ImageTileIntegrator::Render serves requests from
   stdin instead of rendering once. Each request zeroes the region's Film pixels,
   then runs the same wave loop as the qualified batch mode over the region and
   sample range, then closes the logs and acknowledges on stdout.

Transport, sampling, charging, Film accumulation and log formats are not edited.
Equivalence with the qualified per-process bridge is established separately on
the native-validation fixtures (worker-validation contract).
"""
import argparse
import hashlib
import json
from pathlib import Path

from e3_instrument import apply as apply_e3

STREAMS = '''// TC-R1 persistent worker: logs reopen when their environment path changes.
static std::string tcr1Paths[3];
static std::ofstream tcr1Streams[3];
static std::ofstream &TCR1Stream(int slot, const char *path) {
    if (tcr1Paths[slot] != path) {
        if (tcr1Streams[slot].is_open()) tcr1Streams[slot].close();
        tcr1Streams[slot].clear();
        tcr1Streams[slot].open(path);
        tcr1Paths[slot] = path;
    }
    return tcr1Streams[slot];
}
static void TCR1CloseStreams() {
    for (int slot = 0; slot < 3; ++slot) {
        if (tcr1Streams[slot].is_open()) {
            tcr1Streams[slot].close();
            if (!tcr1Streams[slot]) ErrorExit("TC-R1 worker: log close failed");
        }
        tcr1Streams[slot].clear();
        tcr1Paths[slot].clear();
    }
}
'''

WORKER = '''
    // TC-R1 persistent worker: serve region/sample-range requests from stdin.
    if (std::getenv("TC_R1W_WORKER")) {
        ThreadLocal<ScratchBuffer> scratchBuffers([]() { return ScratchBuffer(); });
        ThreadLocal<Sampler> samplers([this]() { return samplerPrototype.Clone(); });
        Bounds2i filmBounds = camera.GetFilm().PixelBounds();
        std::printf("TCR1W READY\\n");
        std::fflush(stdout);
        std::string line;
        while (std::getline(std::cin, line)) {
            std::istringstream request(line);
            int x0, x1, y0, y1, begin, end;
            std::string samplesPath, eventsPath, filmPath;
            if (!(request >> x0 >> x1 >> y0 >> y1 >> begin >> end >> samplesPath >> eventsPath >> filmPath))
                ErrorExit("TC-R1 worker: malformed request");
            Bounds2i region(Point2i(x0, y0), Point2i(x1, y1));
            if (x0 < filmBounds.pMin.x || y0 < filmBounds.pMin.y || x1 > filmBounds.pMax.x ||
                y1 > filmBounds.pMax.y || x0 >= x1 || y0 >= y1 || begin < 0 || begin >= end ||
                end > samplerPrototype.SamplesPerPixel())
                ErrorExit("TC-R1 worker: invalid request bounds");
            setenv("TC_R1E_SAMPLE_LOG", samplesPath.c_str(), 1);
            setenv("TC_R1E2_EVENTS", eventsPath.c_str(), 1);
            setenv("TC_R1E2_FILM", filmPath.c_str(), 1);
            for (Point2i p : region)
                camera.GetFilm().ResetPixel(p);
            int waveStart = begin, waveEnd = begin + 1, nextWaveSize = 1;
            while (waveStart < end) {
                ParallelFor2D(region, [&](Bounds2i tileBounds) {
                    ScratchBuffer &scratchBuffer = scratchBuffers.Get();
                    Sampler &sampler = samplers.Get();
                    for (Point2i pPixel : tileBounds)
                        for (int sampleIndex = waveStart; sampleIndex < waveEnd; ++sampleIndex) {
                            sampler.StartPixelSample(pPixel, sampleIndex);
                            EvaluatePixelSample(pPixel, sampleIndex, sampler, scratchBuffer);
                            scratchBuffer.Reset();
                        }
                });
                waveStart = waveEnd;
                waveEnd = std::min(end, waveEnd + nextWaveSize);
                nextWaveSize = std::min(2 * nextWaveSize, 64);
            }
            TCR1CloseStreams();
            unsetenv("TC_R1E_SAMPLE_LOG");
            unsetenv("TC_R1E2_EVENTS");
            unsetenv("TC_R1E2_FILM");
            std::printf("TCR1W DONE %d %d %d %d %d %d\\n", x0, x1, y0, y1, begin, end);
            std::fflush(stdout);
        }
        return;
    }
'''


def apply(root):
    manifest = apply_e3(root)
    path = root/'src/pbrt/cpu/integrators.cpp'
    source = path.read_text()

    def replace(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError('ambiguous worker anchor: '+old[:70])
        source = source.replace(old, new)

    replace('#include <mutex>\n', '#include <mutex>\n#include <cstdio>\n#include <iostream>\n#include <sstream>\n#include <string>\n')
    replace('static void E2Charge(const char *kind) {', STREAMS+'static void E2Charge(const char *kind) {')
    replace('        static std::ofstream out(p);\n        if (!out) ErrorExit("Cannot write E2 events");',
            '        std::ofstream &out = TCR1Stream(1, p);\n        if (!out) ErrorExit("Cannot write E2 events");')
    replace('        static std::ofstream qLog(qPath);',
            '        std::ofstream &qLog = TCR1Stream(0, qPath);')
    replace('        static std::ofstream out(p);\n        if (!out) ErrorExit("Cannot write E2 Film values");',
            '        std::ofstream &out = TCR1Stream(2, p);\n        if (!out) ErrorExit("Cannot write E2 Film values");')
    replace('void ImageTileIntegrator::Render() {\n', 'void ImageTileIntegrator::Render() {'+WORKER)
    path.write_text(source, encoding='utf-8', newline='\n')
    manifest['worker_source_sha256'] = hashlib.sha256(source.encode()).hexdigest()
    manifest['worker_layer'] = 'experiments/tc-r1/worker_instrument.py over unchanged e3_instrument.py'
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(apply(args.source), indent=2)+'\n')
