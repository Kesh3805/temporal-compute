"""Observe native transmission flags without changing E2 charging or transport."""
import argparse
import hashlib
import json
from pathlib import Path

from e2_instrument import apply as apply_e2

PREREGISTRATION = 'b8b63e22f4b8b47267eeb8a281e8c980c68b2197'


def apply(root):
    manifest=apply_e2(root)
    path=root/'src/pbrt/cpu/integrators.cpp'
    source=path.read_text()
    anchor='E2Charge("continuation");'
    if source.count(anchor)!=1:
        raise ValueError('native continuation observation anchor changed')
    source=source.replace(anchor,anchor+'''
        if (bs->IsTransmission()) {
            if (const char *p = std::getenv("TC_R1E3_TRANSMISSION")) {
                static std::mutex mutex;
                std::lock_guard<std::mutex> lock(mutex);
                static std::ofstream out(p);
                if (!out) ErrorExit("Cannot write E3 transmission observations");
                out << e2x << ',' << e2y << ',' << e2index << ',' << e2continuation << '\\n';
            }
        }''')
    path.write_text(source,encoding='utf-8',newline='\n')
    manifest['e3_source_sha256']=hashlib.sha256(source.encode()).hexdigest()
    manifest['e3_preregistration']=PREREGISTRATION
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    args=parser.parse_args()
    args.manifest.parent.mkdir(parents=True,exist_ok=True)
    args.manifest.write_text(json.dumps(apply(args.source),indent=2)+'\n')
