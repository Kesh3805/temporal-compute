"""Explicit model provisioning only. Scoring never downloads models."""
import argparse
import shutil
import urllib.request
from pathlib import Path

from metrics import WEIGHTS, verify_hash


def prepare(directory):
    import lpips
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    backbone = directory/'alexnet-owt-7be5be79.pth'
    if not backbone.exists():
        temporary = directory/'alexnet-download.tmp'
        urllib.request.urlretrieve('https://download.pytorch.org/models/alexnet-owt-7be5be79.pth', temporary)
        verify_hash(temporary, WEIGHTS[backbone.name])
        temporary.replace(backbone)
    verify_hash(backbone, WEIGHTS[backbone.name])
    calibration = Path(lpips.__file__).parent/'weights/v0.1/alex.pth'
    verify_hash(calibration, WEIGHTS['alex.pth'])
    shutil.copyfile(calibration, directory/'alex.pth')
    return {name: digest for name, digest in WEIGHTS.items()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    print(prepare(parser.parse_args().directory))
