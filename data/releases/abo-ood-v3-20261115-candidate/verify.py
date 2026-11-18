"""Verify OOD tables, review bindings, and optionally downloaded images."""
import argparse,csv,hashlib,json
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parent


def safe_image(value):
    p=PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or not p.parts or p.parts[0]!='small':raise ValueError('Unsafe image path')
    return ROOT/'images'/str(p)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--images',action='store_true');args=ap.parse_args()
    sha=lambda p:hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    for filename in ('manifest.json','screening_manifest.json'):
        m=json.loads((ROOT/filename).read_text())
        for name,expected in m['output_sha256'].items():
            if sha(ROOT/name)!=expected:raise ValueError('Hash mismatch: '+name)
    m=json.loads((ROOT/'screening_manifest.json').read_text())
    for name,expected in m['input_sha256'].items():
        path=ROOT/name if name!='decisions.csv' else ROOT.parent.parent/'reviews/ood-v3-model-assisted/decisions.csv'
        if sha(path)!=expected:raise ValueError('Review input hash mismatch: '+str(path))
    with (ROOT/'image_manifest.csv').open() as f:images=list(csv.DictReader(f))
    if args.images:
        for r in images:
            if hashlib.sha256(safe_image(r['image_path']).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Image hash mismatch')
    print('OOD table/review hashes verified; images checked='+str(args.images))


if __name__=='__main__':main()
