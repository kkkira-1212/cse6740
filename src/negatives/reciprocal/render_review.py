"""Render an offline N3 review UI; generated image HTML stays outside Git."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from build_balanced_n3 import FIELDS, read

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from build_review import create_page


def main():
    root=Path(__file__).resolve().parents[3]
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--sample-csv',type=Path,default=root/'data/reviews/n3-reciprocal-dev-v1/review_sample.csv')
    ap.add_argument('--image-root',type=Path,default=root/'data/releases/abo-home-v2-20261103/images')
    ap.add_argument('--image-manifest',type=Path,default=root/'data/releases/abo-home-v2-20261103/image_manifest.csv')
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();rows=read(args.sample_csv)
    if not rows or len({r['dataset_id'] for r in rows})!=1:
        raise ValueError('Expected a nonempty single-batch review sample')
    title=f'N3 双向颜色替换 · {len(rows)} 条人工审核'
    result=create_page(rows,args.image_root,args.out,title=title)
    if result['image_failures']:
        args.out.unlink(missing_ok=True)
        raise ValueError('Missing or invalid review images; no usable HTML written')
    expected={r['image_path']:r['sha256'] for r in read(args.image_manifest)}
    for r in rows:
        if hashlib.sha256((args.image_root/r['image_path']).read_bytes()).hexdigest()!=expected.get(r['image_path']):
            args.out.unlink(missing_ok=True)
            raise ValueError('Review image differs from source release: '+r['image_path'])
    text=args.out.read_text(encoding='utf-8');batch=rows[0]['dataset_id']
    text=text.replace(result['dataset_id'],batch)
    text=text.replace('CSE 6740 · SEAN / WP3 · HUMAN REVIEW','CSE 6740 · N3 RECIPROCAL · DEVELOPMENT REVIEW')
    text=text.replace('这里都是自动生成的候选负例，尚未通过人工审核。N2 换图片，N3 改颜色。原始记录仅供核查，最终以当前配对的图片和标题为准。',
        '相邻两条为一组双向颜色交换，请逐条独立判断。只改颜色；颜色不清、多色、近似色或原始关联有问题时可选「无法判断」并备注。')
    types=sorted({r['neg_type'] for r in rows})
    options='<option value="all">全部样本</option>'+''.join(f'<option value="{kind}">{kind}</option>' for kind in types if kind in {'N3R','N3R2'})
    if not set(types)<={'N3R','N3R2'}:raise ValueError('Unsupported reciprocal review type')
    text=text.replace('<option value="all">全部类型</option><option>N1</option><option>N2</option><option>N3</option>',options)
    text=text.replace("key='sean-review-","key='n3-reciprocal-review-")
    old="const fields=['pair_id','neg_type','split','category','text_item_id','image_item_id','image_path','original_text','text','attribute','old_value','new_value','review_decision','reason','notes'];"
    if old not in text:raise ValueError('Review template export format changed')
    text=text.replace(old,'const fields='+json.dumps(FIELDS)+';')
    text=text.replace('sean_review_completed.csv','n3_reciprocal_review_completed.csv').replace('sean_review_backup.json','n3_reciprocal_review_backup.json')
    if types==['N3R2']:
        text=text.replace('n3_reciprocal_review_completed.csv','n3_expanded_review_completed.csv').replace('n3_reciprocal_review_backup.json','n3_expanded_review_backup.json')
    text=text.replace('假负例率：','本批匹配标记率：')
    text=text.replace("if(r.old_value)details.append(node('p',`替换：${r.old_value} → ${r.new_value}`));",
        "if(r.old_value)details.append(node('p',`颜色替换：${r.old_value} → ${r.new_value}`));details.append(node('p',`交换组：${r.exchange_id}`));details.append(node('p',`颜色表达来源标题：${r.donor_original_text}`));")
    text=text.replace("const m=new Map(rows.map(r=>[r.pair_id,r]));for(const v of d.decisions)",
        "const m=new Map(rows.map(r=>[r.pair_id,r]));if(d.decisions.length!==rows.length||new Set(d.decisions.map(v=>v.pair_id)).size!==rows.length)throw Error('备份缺少记录或包含重复编号');for(const v of d.decisions)")
    args.out.write_text(text,encoding='utf-8')
    print(json.dumps(dict(rows=len(rows),images=result['images'],dataset_id=batch,out=str(args.out))))


if __name__=='__main__':main()
