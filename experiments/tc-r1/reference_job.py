"""One matrix job of reference production: verified corpus frame `index`, one stream, one level."""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from reference_pipeline import corpus_plans  # noqa: E402
from reference_producer import produce  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--index', type=int, required=True)
    parser.add_argument('--stream', choices=('reference-a', 'reference-b'), required=True)
    parser.add_argument('--spp', type=int, required=True)
    parser.add_argument('--frames', default='all')
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    plans = corpus_plans(ROOT, ROOT/'research/tc-r1/corpus/manifest.json')
    plan = plans['pairs'][args.index]
    key = f"{plan['scene_id']}/{plan['frame_id']}"
    if args.frames != 'all' and key not in set(args.frames.split(',')):
        print(json.dumps(dict(skipped=key)))
        return
    manifest = json.loads((ROOT/'research/tc-r1/corpus/manifest.json').read_text(encoding='utf-8'))
    path = next(f['path'] for s in manifest['scenes'] if s['scene_id'] == plan['scene_id']
                for f in s['frames'] if f['frame_id'] == plan['frame_id'])
    stem = f"{plan['scene_id']}-{plan['frame_id']}-{args.stream}-{args.spp}"
    record = produce(args.binary, args.manifest, ROOT/path, plan['scene_id'], plan['frame_id'], plan['asset_sha256'],
                     plans['corpus_sha256'], args.spp, args.stream, args.threads, Path(args.output)/f'{stem}.npy')
    print(json.dumps(dict(frame=key, stream=args.stream, spp=args.spp, sha256=record['sha256'],
                          seconds=record['elapsed_ns']/1e9)))


if __name__ == '__main__':
    main()
