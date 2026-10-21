"""CPU inference for the same all-MiniLM-L6-v2 encoder used by Kira.

Uses the model author's full precision ONNX export, attention-mask mean pooling,
L2 normalization, and SentenceTransformer's 256 token limit. No CLIP mining.
Source: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
Dependencies: numpy, onnxruntime, tokenizers. Resolved model revision is recorded.
"""
import json
import os
from pathlib import Path
import urllib.request


def encode(titles, cache, revision=None, batch_size=32):
    # Official full-lifetime opt-out MUST precede ONNX Runtime import:
    # https://github.com/microsoft/onnxruntime/blob/main/docs/Privacy.md
    # The API alone may be too late for the initialization event.
    os.environ['ORT_DISABLE_TELEMETRY'] = '1'
    import numpy as np
    import onnxruntime as ort
    ort.disable_telemetry_events()
    from tokenizers import Tokenizer
    model = 'sentence-transformers/all-MiniLM-L6-v2'
    if revision is None:
        with urllib.request.urlopen('https://huggingface.co/api/models/' + model, timeout=45) as f:
            revision = json.load(f)['sha']
    root = Path(cache) / revision
    for filename in ['tokenizer.json', 'onnx/model.onnx']:
        path = root / filename
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            url = f'https://huggingface.co/{model}/resolve/{revision}/{filename}'
            temporary = path.with_suffix(path.suffix + '.part')
            with urllib.request.urlopen(url, timeout=120) as source, temporary.open('wb') as dest:
                while chunk := source.read(1024 * 1024):
                    dest.write(chunk)
            temporary.replace(path)
    tokenizer = Tokenizer.from_file(str(root / 'tokenizer.json'))
    tokenizer.enable_truncation(max_length=256)
    tokenizer.enable_padding(pad_id=0, pad_token='[PAD]')
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 2
    session = ort.InferenceSession(str(root / 'onnx/model.onnx'), sess_options=opts,
                                   providers=['CPUExecutionProvider'])
    names = {i.name for i in session.get_inputs()}
    embeddings = []
    for start in range(0, len(titles), batch_size):
        tokens = tokenizer.encode_batch(titles[start:start + batch_size])
        feed = {'input_ids': np.array([t.ids for t in tokens], dtype=np.int64),
                'attention_mask': np.array([t.attention_mask for t in tokens], dtype=np.int64),
                'token_type_ids': np.array([t.type_ids for t in tokens], dtype=np.int64)}
        output = session.run(None, {k: v for k, v in feed.items() if k in names})[0]
        mask = feed['attention_mask'][..., None]
        pooled = (output * mask).sum(1) / np.maximum(mask.sum(1), 1)
        pooled /= np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12)
        embeddings.append(pooled.astype(np.float32))
    return np.concatenate(embeddings), {'model': model, 'revision': revision,
                                       'backend': 'onnx_float32', 'max_seq_length': 256}
