# Homework 6 — Campus Customs Vendor Desk Agent

A vendor-desk agent that reads a vendor document (HTML, PDF, or `.eml` email), pulls out the key
facts (vendor, SKU, unit price, lead time, minimum order), and recommends **recommend** or
**do_not_recommend** following the Campus Customs Shop Handbook. The homework also measures the
token cost of running it, attacks it with prompt-injection documents, and defends it.

## AI provider

This project uses the **Portkey** gateway for every AI call (the direct OpenAI key ran out of
credits; the Portkey key is the one that works, and it still reaches the required model).

- **Model:** `gpt-6-luna` only (read from `PORTKEY_MODEL`) — no other model is used anywhere.
- **Key / gateway:** `PORTKEY_API_KEY` and `PORTKEY_BASE_URL`, read from a local `.env`.
- The real `.env` is never committed. `.env.example` lists the variable names only.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env     # then fill in your real Portkey key
```

## Run the agent on one document

```bash
python agent.py --doc data/practice_docs/p01_bluehen_quote.html
```

This reads the document, logs the answer, the tool calls, and the cost, and prints the
recommendation.

## Layout

- `agent.py`, `tools.py`, `models.py` — the agent
- `prompts/prompt.md` — the agent's instructions
- `data/` — course data (handbook, prices, practice/exam docs, answer key) plus `my_attacks/`
- `output/` — all results, logs, estimates, and the final `hw6_report.html`
- `AI_prompts.md` — log of what I typed to my vibe coder, one section per problem
