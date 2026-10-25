# Problem 4 — With and Without Cached Tokens

The handbook (~10k tokens) is identical on every call, so the model can reuse it from
cache at ~1/10th the input price. This tests what that is actually worth. The agent ran
on all 12 practice documents two ways; every call is saved in `output/cache_test.json`.

## Setup and proof (the API's own token counts)

- **With cache:** the system prompt (handbook) is byte-for-byte identical on every call,
  so OpenAI reuses the prefix from cache.
- **Without cache:** a unique ~175-token nonce is prepended to the prompt on **every model
  request** (not just every document — each document run makes two model calls, so the
  nonce is regenerated per request), so the prefix never matches and nothing is reused.

| Setup | Total cached tokens (API) | Proof |
|---|---|---|
| With cache | **248,280** | cache is being reused ✅ |
| Without cache | **0** | nothing reused ✅ (a no-cache run showing cached tokens would not count) |

## Per-call token counts and cost

| Document | With: input / cached / out / $ | Without: input / cached / out / $ |
|---|---|---|
| p01_bluehen_quote.html | 22,016 / 10,808 / 200 / $0.001329 | 22,376 / 0 / 215 / $0.002345 |
| p02_elmcity_quote.html | 22,018 / 21,588 / 203 / $0.000360 | 22,373 / 0 / 228 / $0.002351 |
| p03_ivyprint_catalog.html | 22,016 / 21,588 / 243 / $0.000380 | 22,362 / 0 / 256 / $0.002364 |
| p04_harborstitch_quote.html | 22,051 / 21,590 / 194 / $0.000359 | 22,407 / 0 / 174 / $0.002328 |
| p05_maplemills_quote.pdf | 21,984 / 21,588 / 138 / $0.000324 | 22,326 / 0 / 151 / $0.002308 |
| p06_qtextile_quote.pdf | 22,028 / 21,588 / 157 / $0.000338 | 22,379 / 0 / 152 / $0.002314 |
| p07_longwharf_quote.pdf | 22,003 / 21,588 / 254 / $0.000384 | 22,353 / 0 / 230 / $0.002350 |
| p08_chapelst_email.eml | 21,978 / 21,589 / 190 / $0.000350 | 22,319 / 0 / 160 / $0.002312 |
| p09_westville_email.eml | 22,108 / 21,589 / 467 / $0.000501 | 22,463 / 0 / 385 / $0.002439 |
| p10_eastrock_email.eml | 21,997 / 21,589 / 162 / $0.000338 | 22,338 / 0 / 196 / $0.002332 |
| p11_yorkst_quote.html | 21,980 / 21,588 / 173 / $0.000342 | 22,341 / 0 / 134 / $0.002301 |
| p12_bluehen_quote.pdf | 22,002 / 21,587 / 179 / $0.000347 | 22,368 / 0 / 157 / $0.002315 |

## Totals, per-document cost, and savings

| Setup | Total cost (12 docs) | Cost per document |
|---|---|---|
| **With cache** | **$0.005353** | **$0.000446** |
| **Without cache** | **$0.028060** | **$0.002338** |
| **Saved** | **$0.022707** | **80.9%** |

Pricing from `data/prices.json`: input $0.10/1M, cached input $0.01/1M, output $0.50/1M.

## How the real numbers compare to the Problem 2 estimate

Problem 2 estimated the **handbook alone** (10,058 tokens): ~$0.001006/call uncached and
~$0.000101/call cached — about a **90%** cut on the handbook portion.

- **Direction confirmed:** caching the handbook is the big lever, and the real runs show a
  large cut (80.9% on the full call).
- **Why real per-call cost is higher than the P2 handbook-only figure** ($0.002338 uncached
  vs $0.001006): each document run is **two model calls** (the agent calls `read_document`,
  then answers), and every call re-sends the whole handbook. So the real call carries ~2×
  the handbook plus the document text, the instructions, and the output.
- **Why the real saving (80.9%) is a bit below the 90% P2 predicted:** only the repeated
  prefix (the handbook) gets the cache discount. The document text, the output tokens, and
  the first (cold) call are not cached, so they dilute the handbook's 90% saving down to
  ~81% of the whole bill.

## Projection — 1,000 documents a day for 30 days (30,000 documents)

| Setup | 30-day cost |
|---|---|
| With cache | **$13.38** |
| Without cache | **$70.15** |
| **Saved** | **$56.77** |

At real vendor-mail volume, caching the handbook turns a ~$70/month model bill into ~$13 —
the same answers, ~81% cheaper, just by reusing the handbook instead of resending it fresh.

## What surprised us, and why it happens

1. **Cached tokens (~21,588) are more than double the handbook (~10,058).** Each run makes
   two model calls and the handbook rides along on both; the cached count is summed across
   both calls, so it lands near 2× the handbook. Lesson: a tool-using agent pays for its
   big fixed context *per model call*, not per document — which makes caching matter even
   more for multi-step agents.
2. **The first document (p01) only cached 10,808 while the rest cached ~21,588.** p01 was
   the cold **cache write** — the prefix had to be stored before it could be reused — so its
   cost ($0.001329) is noticeably higher than every later cached doc (~$0.00035). This is
   exactly the "first call writes, later calls read" pattern from Problem 2, visible in real
   data.
3. **Without-cache cost per doc is almost identical across all 12 (~$0.00233).** With nothing
   reused, cost is driven almost entirely by the fixed handbook that is resent every time —
   the vendor document itself is tiny by comparison, so the documents barely differ in price.
