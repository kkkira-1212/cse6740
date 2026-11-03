"""Fetch and SHA-256 verify the release images. Run from any directory."""
import argparse,csv,hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path,PurePosixPath
import urllib.request
ROOT=Path(__file__).resolve().parents[1]

def one(row):
    rel=PurePosixPath(row['image_path'])
    if rel.is_absolute() or '..' in rel.parts or rel.parts[0]!='small':raise ValueError('Unsafe image path')
    target=ROOT/'images'/str(rel);target.parent.mkdir(parents=True,exist_ok=True)
    for attempt in range(3):
        try:
            if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==row['sha256']:return
            with urllib.request.urlopen('https://amazon-berkeley-objects.s3.amazonaws.com/images/'+str(rel),timeout=45) as src:data=src.read()
            if hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Image bytes differ from release manifest: '+str(rel))
            temp=target.with_suffix('.part');temp.write_bytes(data);temp.replace(target);return
        except Exception:
            if attempt==2:raise

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--workers',type=int,default=12);a=ap.parse_args()
    with (ROOT/'image_manifest.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        for i,_ in enumerate(pool.map(one,rows),1):
            if i%250==0:print('verified',i,'/',len(rows),flush=True)
    print('All',len(rows),'release images verified.')
