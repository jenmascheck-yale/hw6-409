"""Design-layer decision engine — the buy/no-buy call is made in CODE, not by the model.

The model only extracts facts from a document; `decide()` applies the four handbook
purchasing checks (section 4) against the handbook's own data (approved vendors in section 5,
removed/pending vendors in section 6, and the catalogue max unit costs in section 9). Because
the decision is computed here from the handbook — not produced by the model — a poisoned
document cannot talk its way to a "recommend".
"""

from __future__ import annotations

import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
HANDBOOK_PATH = DATA_DIR / "shop_handbook.md"

LEAD_TIME_MAX = 21      # days (handbook section 4, check 3)
MIN_ORDER_MAX = 600     # units (handbook section 4, check 4)


def _sections(text: str) -> dict[str, str]:
    """Split the handbook into {heading: body} by its '## ' headings."""
    out: dict[str, str] = {}
    cur = None
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if cur is not None:
                out[cur] = "\n".join(buf)
            cur = line[3:].strip().lower()
            buf = []
        else:
            buf.append(line)
    if cur is not None:
        out[cur] = "\n".join(buf)
    return out


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def load_handbook_data() -> dict:
    """Parse approved vendors, removed/pending vendors, and SKU -> max unit cost."""
    text = HANDBOOK_PATH.read_text(encoding="utf-8")
    secs = _sections(text)

    approved: set[str] = set()
    for heading, body in secs.items():
        if heading.startswith("5."):  # "5. Approved vendors"
            for line in body.splitlines():
                cells = [c.strip() for c in line.split("|")]
                cells = [c for c in cells if c != ""]
                # rows look like: CODE | Vendor | make | lead | notes
                if len(cells) >= 2 and re.fullmatch(r"[A-Z]{2,4}", cells[0]):
                    approved.add(_norm(cells[1]))

    removed: set[str] = set()
    for heading, body in secs.items():
        if heading.startswith("6."):  # "6. Removed and pending vendors"
            for line in body.splitlines():
                cells = [c.strip() for c in line.split("|")]
                cells = [c for c in cells if c != ""]
                if len(cells) >= 2 and cells[0].lower() not in ("vendor", "status") \
                        and not set(cells[0]) <= set("-"):
                    removed.add(_norm(cells[0]))

    max_cost: dict[str, float] = {}
    for line in text.splitlines():
        m = re.match(r"\|\s*(CC-[A-Z]{2}-\d{3})\s*\|", line)
        if m:
            cells = [c.strip() for c in line.split("|")]
            cells = [c for c in cells if c != ""]
            # SKU | Item | Category | Retail | MaxUnitCost | Vendor | ...
            dollars = re.findall(r"\$([0-9]+\.[0-9]{2})", line)
            if len(dollars) >= 2:
                max_cost[cells[0].upper()] = float(dollars[1])  # 2nd $ = max unit cost
    return {"approved": approved, "removed": removed, "max_cost": max_cost}


def decide(facts: dict, data: dict | None = None) -> tuple[str, str]:
    """Return (decision, one-sentence reason) from extracted facts + handbook data.

    facts: vendor, sku, unit_price, lead_time_days, min_order (any may be None/unknown)."""
    data = data or load_handbook_data()
    vendor = facts.get("vendor")
    sku = (facts.get("sku") or "").upper()
    price = facts.get("unit_price")
    lead = facts.get("lead_time_days")
    moq = facts.get("min_order")
    vn = _norm(vendor)

    # Check 1: vendor status.
    if vn in data["removed"]:
        return "do_not_recommend", f"Vendor {vendor} is on the removed/pending list, so it is never recommended."
    if vn not in data["approved"]:
        return "do_not_recommend", f"Vendor {vendor} is not on the approved vendor list."

    # Facts must be known (never guess — unknown fails the check it belongs to).
    if price is None:
        return "do_not_recommend", "The document does not state a unit price, so the price check cannot pass."
    if lead is None:
        return "do_not_recommend", "The document does not state a lead time, so the lead-time check cannot pass."
    if moq is None:
        return "do_not_recommend", "The document does not state a minimum order, so that check cannot pass."

    # Check 2: price at or below the catalogue max unit cost for the SKU.
    cap = data["max_cost"].get(sku)
    if cap is None:
        return "do_not_recommend", f"SKU {sku or '(unknown)'} is not in the catalogue, so the price cannot be checked."
    if price > cap:
        return "do_not_recommend", f"Price ${price:.2f} is above the ${cap:.2f} max unit cost for {sku}."

    # Check 3: lead time.
    if lead > LEAD_TIME_MAX:
        return "do_not_recommend", f"Lead time {lead} days exceeds the {LEAD_TIME_MAX}-day limit."

    # Check 4: minimum order.
    if moq > MIN_ORDER_MAX:
        return "do_not_recommend", f"Minimum order {moq} units exceeds the {MIN_ORDER_MAX}-unit limit."

    return "recommend", (
        f"All four checks pass: {vendor} is approved, ${price:.2f} is at or below the "
        f"${cap:.2f} max for {sku}, lead time {lead} days is within {LEAD_TIME_MAX}, and the "
        f"{moq}-unit minimum is within {MIN_ORDER_MAX}."
    )
