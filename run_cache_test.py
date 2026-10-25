"""Problem 4 — run all 12 practice documents with cache and without cache.

With cache: the handbook prefix is identical on every call, so OpenAI reuses it from
cache (cached_tokens > 0 after the first call). Without cache: a unique nonce is
prepended to each call so the prefix never matches (cached_tokens must be 0).

Saves every model call to output/cache_test.json. The token counts the API returns are
the proof each setup did what we think — a without-cache call that still shows cached
tokens would not count.

    python run_cache_test.py
"""

from __future__ import annotations

import json
from pathlib import Path

from agent import DATA_DIR, OUTPUT_DIR, run_document

PRACTICE_DIR = DATA_DIR / "practice_docs"
CACHE_TEST_PATH = OUTPUT_DIR / "cache_test.json"


def practice_docs() -> list[str]:
    return sorted(str(p) for p in PRACTICE_DIR.iterdir() if p.is_file())


def main() -> None:
    docs = practice_docs()
    print(f"Running {len(docs)} practice docs with cache, then without cache...\n")

    records: list[dict] = []
    # With cache first so the identical handbook prefix warms and is reused.
    for doc in docs:
        rec = run_document(doc, cache=True, write_logs=False)
        rec["setup"] = "with_cache"
        records.append(rec)
    # Without cache: each call gets a unique prefix, so nothing is reused.
    for doc in docs:
        rec = run_document(doc, cache=False, write_logs=False)
        rec["setup"] = "without_cache"
        records.append(rec)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_TEST_PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")

    # Quick proof summary to the terminal.
    with_cache = [r for r in records if r["setup"] == "with_cache"]
    without_cache = [r for r in records if r["setup"] == "without_cache"]
    wc_cached = sum(r["cached_tokens"] for r in with_cache)
    nc_cached = sum(r["cached_tokens"] for r in without_cache)
    print("\n================ PROOF ================")
    print(f"with_cache    total cached tokens: {wc_cached}  (expect > 0)")
    print(f"without_cache total cached tokens: {nc_cached}  (MUST be 0)")
    print(f"with_cache    total cost: ${sum(r['cost_usd'] for r in with_cache):.6f}")
    print(f"without_cache total cost: ${sum(r['cost_usd'] for r in without_cache):.6f}")
    print(f"\nSaved {len(records)} calls to {CACHE_TEST_PATH}")


if __name__ == "__main__":
    main()
