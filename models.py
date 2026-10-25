"""Structured types for the Campus Customs vendor desk agent.

`VendorAssessment` is the agent's structured output — the exact set of facts the
handbook (section 13) says the vendor desk must report for each document, plus the
buy/no-buy decision and a one-line reason. `AgentDeps` is the per-run context handed
to the tools so they know which document they are working and where to log traps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from pydantic import BaseModel, Field


@dataclass
class AgentDeps:
    """Context carried into every tool call for one document run.

    `doc_path` is the vendor document the agent was pointed at; `read_document`
    reads exactly this file so the agent cannot be steered to open another path.
    `trap_path` is where the trap tools append if they are ever called.
    """

    doc_path: str
    trap_path: str
    # Defended runs read the sanitized document; undefended runs read it naively (Problem 7).
    defended: bool = False


class VendorFacts(BaseModel):
    """Facts the DEFENDED agent extracts from a document — no decision.

    The decision is computed in code (handbook_rules.decide), so the model's only job is to
    read the five facts off the visible quote. Keeping the decision out of the model is the
    design-layer defense: a poisoned document cannot talk the model into a 'recommend'."""

    vendor: str = Field(description="Vendor name exactly as the visible quote states it.")
    sku: Optional[str] = Field(default=None, description="Campus Customs SKU, or null if not stated.")
    unit_price: Optional[float] = Field(default=None, description="Quoted unit price in USD, or null.")
    lead_time_days: Optional[int] = Field(default=None, description="Lead time in days, or null.")
    min_order: Optional[int] = Field(default=None, description="Minimum order in units, or null.")


class VendorAssessment(BaseModel):
    """The vendor desk's answer for one vendor document.

    Prices/lead time/min order are optional because the handbook says to report a
    fact as unknown (null) when the document does not state it — never guess a number.
    """

    vendor: str = Field(description="Vendor name exactly as the document states it.")
    sku: Optional[str] = Field(
        default=None, description="Campus Customs SKU (e.g. CC-HD-006), or null if not stated."
    )
    unit_price: Optional[float] = Field(
        default=None, description="Quoted unit price in USD, or null if not stated."
    )
    lead_time_days: Optional[int] = Field(
        default=None, description="Lead time in days, or null if not stated."
    )
    min_order: Optional[int] = Field(
        default=None, description="Minimum order in units, or null if not stated."
    )
    decision: Literal["recommend", "do_not_recommend"] = Field(
        description="recommend only if all four handbook checks pass; otherwise do_not_recommend."
    )
    reason: str = Field(
        description="One sentence that names the handbook check which decided the result."
    )
