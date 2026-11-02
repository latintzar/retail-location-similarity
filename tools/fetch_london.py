#!/usr/bin/env python3
"""Fetch the unchanged historical London matrix and verify its size and SHA-256."""
from contextlib import closing
from pathlib import Path
import argparse
import hashlib
import json
import os
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / 'data/london/manifest.json').read_text())


def fetch(destination, *, manifest=MANIFEST, opener=urllib.request.urlopen):
    destination = Path(destination)
    if destination.exists():
        with destination.open('rb') as source:
            digest = hashlib.file_digest(source, 'sha256').hexdigest()
        if destination.stat().st_size == manifest['bytes'] and digest == manifest['sha256']:
            return destination
        raise ValueError(f'Existing file has different bytes; choose another output path: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=destination.name + '.', suffix='.part', dir=destination.parent, delete=False) as target:
            temporary = Path(target.name)
            digest = hashlib.sha256()
            count = 0
            request = urllib.request.Request(manifest['download_url'], headers={'User-Agent': 'RetailLocationSimilarity/1.0'})
            with closing(opener(request, timeout=60)) as response:
                while chunk := response.read(1024 * 1024):
                    count += len(chunk)
                    if count > manifest['bytes']:
                        raise ValueError('Download exceeds expected matrix size')
                    target.write(chunk)
                    digest.update(chunk)
            if count != manifest['bytes'] or digest.hexdigest() != manifest['sha256']:
                raise ValueError('Matrix checksum or byte count differs from the published manifest')
            os.fchmod(target.fileno(), 0o644)
            target.flush()
            os.fsync(target.fileno())
            installed_identity = os.fstat(target.fileno())
        # Exclusive link leaves any destination created concurrently untouched.
        os.link(temporary, destination)
        installed = destination.lstat()
        if (installed.st_dev, installed.st_ino) != (installed_identity.st_dev, installed_identity.st_ino):
            raise FileExistsError('Destination changed during installation; the replacement was preserved')
        return destination
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'data/london-res10.parquet')
    args = parser.parse_args()
    try:
        result = fetch(args.output)
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    print(f'Verified {result} · {MANIFEST["bytes"]:,} bytes · SHA-256 {MANIFEST["sha256"]}')


if __name__ == '__main__':
    main()
