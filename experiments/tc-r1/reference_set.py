"""Bind converged reference pairs into reference-set.json (input to unit jobs and the execution freeze).

Reads one or more convergence-<spp>.json reports (in escalation order) from the
reference directory. A frame's scoring pair is its first converged level.
Frames that halt are listed; frames with no terminal decision block the set.
"""
import argparse
import json
from pathlib import Path


def build(directory):
    directory = Path(directory)
    reports = sorted(directory.glob('convergence-*.json'), key=lambda p: int(p.stem.split('-')[1]))
    if not reports:
        raise ValueError('no convergence reports')
    converged, halted, pending, halted_at = {}, [], set(), {}
    for path in reports:
        report = json.loads(path.read_text(encoding='utf-8'))
        for record in report['records']:
            plan = record['plan']
            key = f"{plan['scene_id']}/{plan['frame_id']}"
            if key in halted and halted_at[key] == 32768 and report.get('extended') and plan['spp'] > 32768:
                # Amendment 0007: a halt at the registered 32768 level continues at extended levels.
                halted.remove(key)
            if key in converged or key in halted:
                raise ValueError(f'work after a terminal decision: {key}')
            stem = f"{plan['scene_id']}-{plan['frame_id']}"
            if record['decision'] == 'converged':
                converged[key] = dict(spp=plan['spp'], a=f"{stem}-reference-a-{plan['spp']}.npy",
                                      b=f"{stem}-reference-b-{plan['spp']}.npy", a_sha256=record['a']['sha256'],
                                      b_sha256=record['b']['sha256'], metrics=record['metrics'])
                pending.discard(key)
            elif record['decision'] == 'halt':
                halted.append(key)
                halted_at[key] = plan['spp']
                pending.discard(key)
            else:
                pending.add(key)
    return dict(schema='tc-r1-reference-set-v1', directory='.', converged=converged, halted=sorted(halted),
                pending=sorted(pending), complete=not pending and len(converged) + len(halted) == 30)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory')
    args = parser.parse_args()
    value = build(args.directory)
    (Path(args.directory)/'reference-set.json').write_text(json.dumps(value, indent=1)+'\n', encoding='utf-8')
    print(json.dumps(dict(converged=len(value['converged']), halted=value['halted'], pending=value['pending'],
                          complete=value['complete'])))


if __name__ == '__main__':
    main()
