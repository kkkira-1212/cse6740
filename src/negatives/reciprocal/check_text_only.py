"""Train-only grouped diagnostics, with old N3 controls on the exact same images."""
import argparse
import json
from pathlib import Path
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, roc_auc_score
from build_balanced_n3 import read

def main():
    repo=Path(__file__).resolve().parents[3]
    ap=argparse.ArgumentParser();ap.add_argument('--data-dir',type=Path,default=repo/'data/reviews/n3-reciprocal-dev-v1');ap.add_argument('--source-audit',type=Path,default=repo/'data/releases/abo-home-v2-20261103/n3_audit.csv');ap.add_argument('--out-json',type=Path);args=ap.parse_args()
    root=args.data_dir
    rows=[r for r in read(root/'n3_with_positives.csv') if r['split']=='train']
    exchange={r['anchor_item_id']:r['exchange_id'] for r in read(root/'n3_candidates.csv')}
    old={r['item_id']:r['text'] for r in read(args.source_audit)}
    y=np.array([int(r['label']) for r in rows]);groups=[exchange[r['anchor_item_id']] for r in rows]
    report=dict(protocol='Train-only 5-fold GroupKFold; both directions and positives of an exchange stay in the same fold. Fixed threshold .5; no val/test tuning. Small exploratory diagnostic.',
                n_train_rows=len(rows),n_exchange_groups=len(set(groups)),results={})
    for name,options in [('word',dict(ngram_range=(1,2))),('character',dict(analyzer='char',ngram_range=(3,5)))]:
        for version in ['old_same_anchors','reciprocal']:
            texts=[r['text'] if version=='reciprocal' or r['label']=='1' else old[r['anchor_item_id']] for r in rows]
            model=make_pipeline(TfidfVectorizer(min_df=1,**options),LogisticRegression(max_iter=1000,random_state=0))
            scores=cross_val_predict(model,texts,y,groups=groups,cv=GroupKFold(5),method='predict_proba')[:,1]
            report['results'][name+'_'+version]=dict(accuracy=float(accuracy_score(y,scores>=.5)),auc=float(roc_auc_score(y,scores)))
    (args.out_json or root/'text_only_diagnostic.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
