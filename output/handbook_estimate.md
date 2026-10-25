# Problem 2 — Handbook token & cost estimate

The Campus Customs Shop Handbook (`data/shop_handbook.md`) goes to the model on **every**
vendor-desk call, so its size sets a floor on what each call costs. This file estimates that
floor. The real per-call numbers are measured in Problem 4 and compared back to these.

## 1. Token count

| Measure | Value |
|---|---|
| Characters | 28,903 |
| Words | 6,127 |
| **Tokens** | **10,058** |

**How I got it:** I tokenized the raw handbook text with OpenAI's `tiktoken` library using the
`o200k_base` encoding, the encoding OpenAI's current GPT‑4o/GPT‑5-class models use.

```python
import tiktoken, pathlib
text = pathlib.Path("data/shop_handbook.md").read_text(encoding="utf-8")
enc = tiktoken.get_encoding("o200k_base")
print(len(enc.encode(text)))   # -> 10058
```

**Caveat:** `gpt-6-luna` is the course model and does not ship a public tokenizer, so there is no
exact encoder for it. `o200k_base` is the closest standard OpenAI encoding and is used here as a
documented proxy. The API returns the true token counts on real calls, so Problem 4 checks this
10,058 estimate against what the API actually bills.

## 2. Prices (from `data/prices.json`, gpt-6-luna, per 1M tokens)

| Rate | $ / 1M tokens |
|---|---|
| Input (uncached) | $0.10 |
| Cached input (read) | $0.01 |
| Cache write | $0.125 |
| Output | $0.50 |

These are the handbook-only estimates — they cover just the 10,058 handbook tokens, not the vendor
document, the prompt, or the model's output, which get added in Problems 3–4.

## 3. Cost of the handbook alone, per call

Formula: `cost = tokens / 1,000,000 × rate`, with `tokens = 10,058`.

| Setup | Math | Cost per call |
|---|---|---|
| **No cache** (full input rate every call) | 10,058 / 1e6 × $0.10 | **$0.001006** |
| **Cache write** (first call only, loads cache) | 10,058 / 1e6 × $0.125 | $0.001257 |
| **Cache read** (every later call) | 10,058 / 1e6 × $0.01 | **$0.000101** |

So after the handbook is cached, each later call pays about **1/10th** of the uncached price for
those 10,058 tokens ($0.000101 vs $0.001006).

## 4. Cost of the handbook alone, over 1,000 calls

Caching model: the handbook is identical on every call, so the first call writes it to cache and
the remaining 999 calls read it from cache (1 write + 999 reads).

| Setup | Math | 1,000-call cost |
|---|---|---|
| **No cache** | 1,000 × $0.001006 | **$1.0058** |
| **With cache** | 1 × $0.001257 + 999 × $0.000101 | **$0.1017** |
| **Savings** | $1.0058 − $0.1017 | **$0.9041 (≈ 89.9%)** |

## 5. Takeaway

The handbook alone costs about **$1.01 per 1,000 calls uncached** and drops to about **$0.10 per
1,000 calls with caching** — roughly a **90% cut** on the handbook portion of every bill, just by
reusing the same handbook from cache. Because the handbook is the biggest fixed part of each
prompt, this is where almost all of the caching savings come from. These figures are revisited
against real API token counts in Problem 4 (`output/cache_test.md`).
