"""WP7: GPT-6 Luna as a zero-shot image-title matching judge.

For each pair the model sees the product's main image and its English title
and returns a match probability 0-100 via structured output. The score file
holds probability / 100 (fixed threshold 0.5, the same number feeds AUC).

Two prompt versions:
  P1  direct judgment
  P2  check category / colour / material / shape first, then judge

Every raw response is appended to a JSONL log, so an interrupted run can be
resumed with the same command. Parse failures are never mapped to a default
score: they are written to a separate pair list (pass it to the evaluator
with --exclude-pair-list) and counted in the summary JSON.

Needs OPENAI_API_KEY in the environment. Uses only `requests`.

Pilot (20 pairs, both prompts), then inspect the summary for cost/latency:
  python src/baselines/luna_baseline.py --prompt P1 --limit 20 --tag pilot
  python src/baselines/luna_baseline.py --prompt P2 --limit 20 --tag pilot

Full run on the stratified subset:
  python src/baselines/luna_baseline.py --prompt P1 \
    --pairs-csv data/processed/luna_subset_test.csv
"""
import argparse
import base64
import json
import os
import random
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

from common import read_pairs, write_scores

MODEL = "gpt-6-luna"
# USD per 1M tokens, from developers.openai.com/api/docs/models/gpt-6-luna (checked 2026-10-28).
PRICE_INPUT, PRICE_CACHED, PRICE_OUTPUT = 0.10, 0.01, 0.50

MATCH_RULE = (
    "A title MATCHES the image if nothing the title states is contradicted by the image. "
    "A title that leaves details out (for example a black chair with a white cushion "
    "titled only 'black chair') still matches. Judge NOT a match only when there is a "
    "clear contradiction: a different product type, a different colour, material or shape, "
    "or a different product altogether. Brand names, sizes and model numbers usually cannot "
    "be verified from a photo; do not count them as contradictions."
)

PROMPTS = {
    "P1": {
        "instructions": (
            "You verify e-commerce listings. You will receive a product's main image and its "
            "title. " + MATCH_RULE + " Report match_probability: your probability, from 0 to "
            "100, that the title matches the image."
        ),
        "schema": {
            "type": "object",
            "properties": {"match_probability": {"type": "integer", "minimum": 0, "maximum": 100}},
            "required": ["match_probability"],
            "additionalProperties": False,
        },
    },
    "P2": {
        "instructions": (
            "You verify e-commerce listings. You will receive a product's main image and its "
            "title. " + MATCH_RULE + " First check four attributes one at a time: category "
            "(what kind of product), colour, material, and shape. For each, answer "
            "'consistent' if the title's claim agrees with the image, 'contradicted' if it "
            "clearly disagrees, or 'not_checkable' if the title does not state it or the image "
            "cannot show it. Then report match_probability: your probability, from 0 to 100, "
            "that the title matches the image."
        ),
        "schema": {
            "type": "object",
            "properties": {
                **{
                    name: {"type": "string", "enum": ["consistent", "contradicted", "not_checkable"]}
                    for name in ("category", "colour", "material", "shape")
                },
                "match_probability": {"type": "integer", "minimum": 0, "maximum": 100},
            },
            "required": ["category", "colour", "material", "shape", "match_probability"],
            "additionalProperties": False,
        },
    },
}

MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def image_data_url(path):
    mime = MIME.get(path.suffix.lower())
    if mime is None:
        raise ValueError(f"unsupported image type: {path}")
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def build_request(row, args):
    prompt = PROMPTS[args.prompt]
    body = {
        "model": args.model,
        "instructions": prompt["instructions"],
        "input": [{
            "role": "user",
            "content": [
                {"type": "input_image", "image_url": image_data_url(Path(args.image_root) / row["image_path"]),
                 "detail": args.detail},
                {"type": "input_text", "text": f"Title: {row['text']}"},
            ],
        }],
        "text": {"format": {"type": "json_schema", "name": f"match_{args.prompt.lower()}",
                            "schema": prompt["schema"], "strict": True}},
        "store": False,
    }
    if args.reasoning_effort != "omit":
        body["reasoning"] = {"effort": args.reasoning_effort}
    return body


def output_text(response):
    """Concatenate output_text parts of message items; return (text, refusal)."""
    texts, refusal = [], None
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for part in item.get("content", []):
            if part.get("type") == "output_text":
                texts.append(part.get("text", ""))
            elif part.get("type") == "refusal":
                refusal = part.get("refusal", "refused")
    return "".join(texts), refusal


def parse(response, prompt_name):
    """Return (probability 0-100, parsed dict, None) or (None, None, failure reason)."""
    if response.get("status") not in (None, "completed"):
        detail = (response.get("incomplete_details") or {}).get("reason", "")
        return None, None, f"status={response.get('status')} {detail}".strip()
    text, refusal = output_text(response)
    if refusal:
        return None, None, f"refusal: {refusal[:200]}"
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None, None, f"invalid json: {text[:200]!r}"
    prob = data.get("match_probability") if isinstance(data, dict) else None
    if isinstance(prob, bool) or not isinstance(prob, (int, float)) or not 0 <= prob <= 100:
        return None, None, f"bad match_probability: {prob!r}"
    missing = [k for k in PROMPTS[prompt_name]["schema"]["required"] if k not in data]
    if missing:
        return None, None, f"missing fields {missing}"
    return float(prob), data, None


def call_api(body, args, session):
    """POST with retries on 429/5xx/network errors. Returns (json, error, seconds)."""
    url = args.base_url.rstrip("/") + "/responses"
    headers = {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"}
    start = time.monotonic()
    error = None
    for attempt in range(args.max_retries + 1):
        try:
            resp = session.post(url, json=body, headers=headers, timeout=args.timeout)
        except requests.RequestException as exc:
            error = f"network: {exc}"
        else:
            if resp.status_code == 200:
                return resp.json(), None, time.monotonic() - start
            error = f"http {resp.status_code}: {resp.text[:300]}"
            if resp.status_code not in (408, 409, 429) and resp.status_code < 500:
                break  # client error: retrying will not help
            retry_after = resp.headers.get("retry-after")
            if retry_after and retry_after.replace(".", "", 1).isdigit():
                time.sleep(float(retry_after))
                continue
        time.sleep(min(60, 2 ** attempt) + random.random())
    return None, error, time.monotonic() - start


def load_log(path, key, retry_parse_failures):
    """Return (done, all_calls) for this (model, prompt, effort, detail).

    done: latest entry per pair_id that needs no new call. A pair whose call
    got a response is done even if parsing failed, so reruns do not hide the
    parse-failure rate; only transport/API errors are retried, unless
    retry_parse_failures is set. all_calls: every logged call (for cost).
    """
    done, all_calls = {}, []
    if not path.exists():
        return done, all_calls
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            entry = json.loads(line)
            if entry.get("key") != key:
                continue
            all_calls.append(entry)
            got_response = entry.get("response_id") is not None
            if entry.get("probability") is not None or (got_response and not retry_parse_failures):
                done[entry["pair_id"]] = entry
    return done, all_calls


def cost_usd(usage):
    if not usage:
        return 0.0
    inp = usage.get("input_tokens", 0)
    cached = (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
    out = usage.get("output_tokens", 0)
    return ((inp - cached) * PRICE_INPUT + cached * PRICE_CACHED + out * PRICE_OUTPUT) / 1e6


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pairs-csv", default="docs/mini_version/pairs.csv")
    ap.add_argument("--image-root", default="data/images")
    ap.add_argument("--splits", nargs="+", default=["test"], help="splits to score (default: test)")
    ap.add_argument("--limit", type=int, help="score only the first N pairs (pilot)")
    ap.add_argument("--prompt", choices=sorted(PROMPTS), required=True)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--reasoning-effort", default="low",
                    choices=("none", "low", "medium", "high", "xhigh", "max", "omit"),
                    help="fixed for the whole run; 'omit' sends no reasoning field")
    ap.add_argument("--detail", default="auto", choices=("auto", "low", "high", "original"))
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--max-retries", type=int, default=5)
    ap.add_argument("--timeout", type=float, default=120)
    ap.add_argument("--base-url", default="https://api.openai.com/v1")
    ap.add_argument("--tag", default="", help="suffix for output names, e.g. 'pilot'")
    ap.add_argument("--out-dir", default="scores")
    ap.add_argument("--log-dir", default="data/luna_logs", help="raw responses (not committed)")
    ap.add_argument("--retry-parse-failures", action="store_true",
                    help="re-call pairs whose earlier response could not be parsed (report this if used)")
    ap.add_argument("--dry-run", action="store_true", help="print the first request (image elided) and exit")
    args = ap.parse_args()

    rows = read_pairs(args.pairs_csv, splits=args.splits, limit=args.limit)
    name = f"luna_{args.prompt.lower()}_effort-{args.reasoning_effort}" + (f"_{args.tag}" if args.tag else "")
    key = f"{args.model}|{args.prompt}|{args.reasoning_effort}|{args.detail}"

    if args.dry_run:
        body = build_request(rows[0], args)
        body["input"][0]["content"][0]["image_url"] = body["input"][0]["content"][0]["image_url"][:60] + "..."
        print(json.dumps(body, indent=2))
        return
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("set OPENAI_API_KEY first")

    log_path = Path(args.log_dir) / f"{name}.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    done, previous_calls = load_log(log_path, key, args.retry_parse_failures)
    todo = [row for row in rows if row["pair_id"] not in done]
    print(f"{name}: {len(rows)} pairs, {len(done)} already done, {len(todo)} to call", flush=True)

    lock = threading.Lock()
    session = requests.Session()
    results = {}

    def work(row):
        body = build_request(row, args)
        response, error, seconds = call_api(body, args, session)
        prob, parsed, reason = parse(response, args.prompt) if response else (None, None, error)
        entry = {"key": key, "pair_id": row["pair_id"], "neg_type": row.get("neg_type"),
                 "probability": prob, "parsed": parsed, "failure": reason, "seconds": round(seconds, 3),
                 "usage": (response or {}).get("usage"), "response_id": (response or {}).get("id")}
        with lock:
            with log_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(entry) + "\n")
        return entry

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(work, row) for row in todo]
        for count, future in enumerate(as_completed(futures), start=1):
            entry = future.result()
            results[entry["pair_id"]] = entry
            if count % 25 == 0 or count == len(futures):
                print(f"  {count}/{len(futures)}", flush=True)

    entries = {**done, **results}
    scores = {pid: e["probability"] / 100 for pid, e in entries.items() if e["probability"] is not None}
    failed = [row["pair_id"] for row in rows if row["pair_id"] not in scores]

    out_dir = Path(args.out_dir)
    score_path = write_scores(out_dir / f"{name}.csv", rows, scores)
    failed_path = out_dir / f"{name}_parse_failures.txt"
    failed_path.write_text("".join(f"{pid}\n" for pid in failed), encoding="utf-8")

    # Cost counts every billed call, including earlier attempts and failures.
    used = [e for e in previous_calls + list(results.values()) if e.get("usage")]
    reasons = {}
    for pid in failed:
        reason = (entries.get(pid) or {}).get("failure") or "unknown"
        reasons[reason[:80]] = reasons.get(reason[:80], 0) + 1
    p2_checks = {}
    if args.prompt == "P2":
        for e in entries.values():
            for field in ("category", "colour", "material", "shape"):
                value = (e.get("parsed") or {}).get(field)
                if value:
                    p2_checks.setdefault(field, {}).setdefault(value, 0)
                    p2_checks[field][value] += 1
    summary = {
        "model": args.model, "prompt": args.prompt, "reasoning_effort": args.reasoning_effort,
        "detail": args.detail, "pairs_csv": args.pairs_csv, "splits": args.splits, "n_pairs": len(rows),
        "retry_parse_failures": args.retry_parse_failures, "n_api_calls": len(used),
        "n_scored": len(scores), "n_parse_failures": len(failed),
        "parse_failure_rate": len(failed) / len(rows), "failure_reasons": reasons,
        "tokens": {
            "input": sum(e["usage"].get("input_tokens", 0) for e in used),
            "output": sum(e["usage"].get("output_tokens", 0) for e in used),
            "reasoning": sum((e["usage"].get("output_tokens_details") or {}).get("reasoning_tokens", 0) for e in used),
        },
        "cost_usd": round(sum(cost_usd(e["usage"]) for e in used), 4),
        "cost_usd_per_1k_pairs": round(1000 * sum(cost_usd(e["usage"]) for e in used) / max(1, len(used)), 4),
        "price_per_1m_tokens": {"input": PRICE_INPUT, "cached_input": PRICE_CACHED, "output": PRICE_OUTPUT},
        "median_seconds_per_call": statistics.median([e["seconds"] for e in entries.values()]) if entries else None,
        "p2_attribute_checks": p2_checks or None,
        "outputs": {"scores": str(score_path), "parse_failures": str(failed_path), "raw_log": str(log_path)},
    }
    (out_dir / f"{name}_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("n_scored", "n_parse_failures", "tokens", "cost_usd",
                                              "median_seconds_per_call")}, indent=2))


if __name__ == "__main__":
    main()
