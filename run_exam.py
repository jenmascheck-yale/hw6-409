"""Problem 8 — run the final DEFENDED agent on all 10 exam documents.

The defended agent is the cheaper one (the handbook is not sent to the model; the decision is
computed in code), and the safe one. Results are not hand-edited. Writes
output/exam_results.json with the exact fields the assignment lists.

    python run_exam.py
"""

from __future__ import annotations

import json
from pathlib import Path

from agent import DATA_DIR, OUTPUT_DIR, TRAP_PATH, run_document

EXAM_DIR = DATA_DIR / "exam_docs"
EXAM_PATH = OUTPUT_DIR / "exam_results.json"


def main() -> None:
    docs = sorted(str(p) for p in EXAM_DIR.iterdir() if p.is_file())
    TRAP_PATH.write_text("[]", encoding="utf-8")  # clean slate so a trap entry means this run

    results = []
    for doc in docs:
        rec = run_document(doc, cache=True, write_logs=False, defended=True)
        a = rec["assessment"]
        name = rec["document"]
        traps = json.loads(TRAP_PATH.read_text(encoding="utf-8"))
        trap_called = any(t["document"] == name for t in traps)
        results.append({
            "file": name,
            "vendor": a["vendor"],
            "sku": a["sku"],
            "unit_price": a["unit_price"],
            "lead_time_days": a["lead_time_days"],
            "min_order": a["min_order"],
            "decision": a["decision"],
            "reason": a["reason"],
            "trap_tool_called": trap_called,
            "input_tokens": rec["input_tokens"],
            "cached_tokens": rec["cached_tokens"],
            "output_tokens": rec["output_tokens"],
            "cost_usd": rec["cost_usd"],
        })

    EXAM_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")

    total = sum(r["cost_usd"] for r in results)
    traps = sum(r["trap_tool_called"] for r in results)
    print("\n================ EXAM RESULTS ================")
    for r in results:
        print(f"  {r['file']:22} {r['vendor'][:22]:22} {str(r['sku']):12} "
              f"${str(r['unit_price']):>7} lead={str(r['lead_time_days']):>4} "
              f"min={str(r['min_order']):>5} {r['decision']}")
    print(f"\n{len(results)} docs | trap calls: {traps} | total cost ${total:.6f}")
    print(f"Saved {EXAM_PATH}")


if __name__ == "__main__":
    main()
