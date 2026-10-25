"""Campus Customs vendor desk agent — entry point.

Reads one vendor document, extracts the key facts, and recommends buy / do-not-buy by
the Shop Handbook, using ONLY gpt-6-luna through the Portkey gateway. After each run it
logs token usage + cost (output/usage_log.json) and every tool call + the final answer
(output/audit_trail.json), and it guarantees output/trap_calls.json exists as a list.

    python agent.py --doc data/practice_docs/p01_bluehen_quote.html

This is the BASELINE agent (no injection defenses) — Problem 5 attacks it, Problem 6 adds
defenses behind a flag.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from handbook_rules import decide, load_handbook_data
from models import AgentDeps, VendorAssessment, VendorFacts
from tools import approve_payment, read_document, send_email

HW6_DIR = Path(__file__).resolve().parent
DATA_DIR = HW6_DIR / "data"
OUTPUT_DIR = HW6_DIR / "output"
PROMPT_PATH = HW6_DIR / "prompts" / "prompt.md"
PROMPT_DEFENDED_PATH = HW6_DIR / "prompts" / "prompt_defended.md"
HANDBOOK_PATH = DATA_DIR / "shop_handbook.md"
PRICES_PATH = DATA_DIR / "prices.json"
TRAP_PATH = OUTPUT_DIR / "trap_calls.json"
USAGE_PATH = OUTPUT_DIR / "usage_log.json"
AUDIT_PATH = OUTPUT_DIR / "audit_trail.json"

# Load the real key: prefer a local hw6/.env, fall back to the course-root .env
# (kept outside the submission folder so it never reaches GitHub).
for candidate in [HW6_DIR / ".env", HW6_DIR.parent.parent / ".env"]:
    if candidate.exists():
        load_dotenv(candidate)
        break

MODEL_NAME = os.getenv("PORTKEY_MODEL", "gpt-6-luna")
API_KEY = os.getenv("PORTKEY_API_KEY")
BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")


# --------------------------------------------------------------------------- #
# Model + agent
# --------------------------------------------------------------------------- #

def build_model() -> OpenAIResponsesModel:
    """gpt-6-luna routed through Portkey (auth via the x-portkey-api-key header)."""
    if not API_KEY:
        raise RuntimeError(
            "PORTKEY_API_KEY is not set. Add it to hw6/.env or the course-root .env "
            "(see .env.example)."
        )
    client = AsyncOpenAI(
        api_key="unused",
        base_url=BASE_URL,
        default_headers={"x-portkey-api-key": API_KEY},
    )
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


def _cache_bust_nonce() -> str:
    """A unique prefix so OpenAI's prefix cache cannot match (forces 0 cached).

    ~175 tokens (8 x ~24): just over OpenAI's ~128-token cache block so the first block
    is fully unique, while keeping the no-cache overhead small for a fair cost comparison."""
    import uuid
    return "".join(f"NOCACHE-{uuid.uuid4().hex} " for _ in range(8))


def build_agent(defended: bool = False, cache: bool = True) -> Agent:
    """Build the vendor desk agent.

    Undefended (Problem 3 baseline, kept for Problem 7): reads the document naively, has the
    trap tools, and the MODEL makes the decision — with the handbook in its system prompt.

    Defended (Problem 6): reads the SANITIZED document, has ONLY `read_document` (the trap
    tools are unreachable), and extracts facts ONLY — the decision is computed in code
    (handbook_rules.decide). The handbook is not sent to the model, since it no longer judges.

    cache=False makes the instructions DYNAMIC: a fresh nonce is prepended on every model
    request, so OpenAI's prefix cache cannot match (cached_tokens stays 0) — the Problem 4
    "without cache" setup."""
    if defended:
        base = PROMPT_DEFENDED_PATH.read_text(encoding="utf-8")
        output_type = VendorFacts
        tools = [read_document]  # design layer: no trap tools reach the document
    else:
        instructions = PROMPT_PATH.read_text(encoding="utf-8")
        handbook = HANDBOOK_PATH.read_text(encoding="utf-8")
        base = instructions.replace("{handbook}", handbook)
        output_type = VendorAssessment
        tools = [read_document, send_email, approve_payment]

    if cache:
        instr = base
    else:
        def instr(_b=base) -> str:
            return _cache_bust_nonce() + "\n\n" + _b

    return Agent(
        build_model(),
        deps_type=AgentDeps,
        output_type=output_type,
        instructions=instr,
        tools=tools,
    )


# --------------------------------------------------------------------------- #
# Cost + logging
# --------------------------------------------------------------------------- #

def _prices() -> dict:
    return json.loads(PRICES_PATH.read_text(encoding="utf-8"))[MODEL_NAME]


def compute_cost(input_tokens: int, cached_tokens: int, output_tokens: int) -> float:
    """Billed cost: uncached input at input rate, cached input at the cached rate,
    output at the output rate (dollars, from prices.json)."""
    p = _prices()
    uncached = max(input_tokens - cached_tokens, 0)
    return round(
        uncached / 1_000_000 * p["input_per_1m"]
        + cached_tokens / 1_000_000 * p["cached_input_per_1m"]
        + output_tokens / 1_000_000 * p["output_per_1m"],
        8,
    )


def _append_json(path: Path, entry) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    except (json.JSONDecodeError, OSError):
        data = []
    data.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _ensure_trap_file() -> None:
    """trap_calls.json must exist as an empty list so an entry can only mean a hijack."""
    if not TRAP_PATH.exists():
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        TRAP_PATH.write_text("[]", encoding="utf-8")


def _short(value, limit: int = 300) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + "…"


def log_usage(doc_name: str, usage, cost: float) -> dict:
    entry = {
        "document": doc_name,
        "time": datetime.now(timezone.utc).isoformat(),
        "model": MODEL_NAME,
        "input_tokens": usage.input_tokens,
        "cached_tokens": usage.cache_read_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
        "cost_usd": cost,
    }
    _append_json(USAGE_PATH, entry)
    return entry


def log_audit(doc_name: str, result, final: VendorAssessment) -> None:
    """Append each tool call (name + args + short result) and the final answer."""
    events: list[dict] = []
    calls: dict[str, tuple] = {}
    for msg in result.all_messages():
        for part in getattr(msg, "parts", []):
            kind = getattr(part, "part_kind", "")
            if kind == "tool-call":
                calls[getattr(part, "tool_call_id", "")] = (
                    getattr(part, "tool_name", "?"),
                    getattr(part, "args", None),
                )
            elif kind == "tool-return":
                name, args = calls.get(
                    getattr(part, "tool_call_id", ""),
                    (getattr(part, "tool_name", "?"), None),
                )
                events.append({
                    "time": datetime.now(timezone.utc).isoformat(),
                    "document": doc_name,
                    "action": "tool",
                    "detail": f"{name}({_short(args) if args is not None else ''})",
                    "result": _short(getattr(part, "content", "")),
                })
    events.append({
        "time": datetime.now(timezone.utc).isoformat(),
        "document": doc_name,
        "action": "final",
        "detail": "vendor_assessment",
        "result": _short(final.model_dump()),
    })
    for e in events:
        _append_json(AUDIT_PATH, e)


# --------------------------------------------------------------------------- #
# Run one document
# --------------------------------------------------------------------------- #

def resolve_doc(doc: str) -> Path:
    p = Path(doc)
    if p.exists():
        return p
    alt = HW6_DIR / doc
    if alt.exists():
        return alt
    raise FileNotFoundError(f"Vendor document not found: {doc}")


def run_document(doc: str, cache: bool = True, write_logs: bool = True,
                 defended: bool = False) -> dict:
    """Run the agent on one document and return usage + cost + the assessment.

    defended=True reads the sanitized doc, extracts facts only, and computes the decision in
    code. defended=False is the Problem 3 baseline (model decides, trap tools reachable).
    cache=False uses dynamic nonce'd instructions so nothing is reused from cache.
    write_logs=True appends to usage_log.json + audit_trail.json."""
    doc_path = resolve_doc(doc)
    doc_name = doc_path.name
    _ensure_trap_file()

    agent = build_agent(defended=defended, cache=cache)
    deps = AgentDeps(doc_path=str(doc_path), trap_path=str(TRAP_PATH), defended=defended)
    verb = "extract the facts" if defended else "return the structured assessment"
    result = agent.run_sync(
        f"Read the vendor document at {doc_name}. Call read_document to read it, then {verb}.",
        deps=deps,
    )

    usage = result.usage
    cost = compute_cost(usage.input_tokens, usage.cache_read_tokens, usage.output_tokens)

    if defended:
        facts = result.output  # VendorFacts — no decision
        decision, reason = decide(facts.model_dump())
        out = VendorAssessment(
            vendor=facts.vendor, sku=facts.sku, unit_price=facts.unit_price,
            lead_time_days=facts.lead_time_days, min_order=facts.min_order,
            decision=decision, reason=reason,
        )
    else:
        out = result.output

    if write_logs:
        log_usage(doc_name, usage, cost)
        log_audit(doc_name, result, out)

    record = {
        "setup": ("defended" if defended else "undefended") + ("" if cache else "_no_cache"),
        "document": doc_name,
        "input_tokens": usage.input_tokens,
        "cached_tokens": usage.cache_read_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
        "cost_usd": cost,
        "assessment": out.model_dump(),
    }
    print(f"\n=== {doc_name} [{record['setup']}] ===")
    print(json.dumps(out.model_dump(), indent=2))
    print(
        f"tokens: input={usage.input_tokens} cached={usage.cache_read_tokens} "
        f"output={usage.output_tokens} | cost=${cost:.6f}"
    )
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description="Campus Customs vendor desk agent")
    parser.add_argument("--doc", required=True, help="Path to one vendor document")
    parser.add_argument("--no-defense", action="store_true",
                        help="Run the UNDEFENDED baseline agent (Problem 3/5/7) instead of the "
                             "defended agent")
    parser.add_argument("--no-cache", action="store_true",
                        help="Bust the prompt cache (nothing reused) — for the Problem 4 test")
    args = parser.parse_args()
    run_document(args.doc, cache=not args.no_cache, defended=not args.no_defense)


if __name__ == "__main__":
    main()
