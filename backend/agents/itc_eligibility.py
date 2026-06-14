"""ITC Eligibility Agent — the cited-decision hero.

For each purchase it screens for a Section 17(5) blocked-credit category from the
description/HSN, then **grounds the decision in the knowledge base** and attaches
the returned citation. The flag is only asserted when retrieval is confident;
otherwise the agent defers to a human ("consult a CA") instead of guessing — the
Reliability/Safety guardrail from the build plan.

Every blocked flag carries the exact GST Act section + snippet, so the citation
can appear live on screen in the demo regardless of whether the local KB or real
Foundry IQ served it.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.audit.log import AuditLog
from backend.foundry_iq.base import KnowledgeBase
from backend.foundry_iq.factory import get_knowledge_base
from backend.ontology.entities import Citation, PurchaseEntry

AGENT = "ITC Eligibility Agent"


@dataclass
class _Category:
    name: str
    expected_section: str  # prefix to prefer among returned citations
    keywords: tuple[str, ...]
    hsn_prefixes: tuple[str, ...]
    query: str


# Screening rules. The *rule* nominates a candidate; the *knowledge base* supplies
# the authoritative, cited basis for the decision.
CATEGORIES: list[_Category] = [
    _Category(
        # Note: only *consumption* of food/catering is blocked. Packaged food
        # bought for resale by a kirana store keeps ITC (same-category outward
        # supply proviso), so triggers are catering/restaurant/staff-meal signals
        # — not the bare word "food".
        "Food & beverages / outdoor catering",
        "Section 17(5)(b)(i)",
        ("caterer", "catering", "restaurant", "staff lunch", "staff meal",
         "staff party", "office party", "canteen", "refreshment", "outdoor catering"),
        ("9963",),  # 9963 = restaurant/catering *service*
        "input tax credit on food and beverages outdoor catering restaurant",
    ),
    _Category(
        "Construction of immovable property",
        "Section 17(5)(d)",
        ("construction", "building", "civil work", "cement", "renovation",
         "immovable", "shop floor", "interior", "flooring"),
        ("9954",),
        "input tax credit on goods or services for construction of immovable property building",
    ),
    _Category(
        "Motor vehicle",
        "Section 17(5)(a)",
        ("motor vehicle", "car", "motorcycle", "bike", "scooter", "passenger vehicle"),
        ("8703",),
        "input tax credit on motor vehicles for transportation of persons",
    ),
    _Category(
        "Personal consumption / gifts / free samples",
        "Section 17(5)(g)",
        ("personal", "gift", "free sample", "donation", "diwali gift"),
        (),
        "input tax credit on goods used for personal consumption or gifts free samples",
    ),
    _Category(
        "Club / health & fitness membership",
        "Section 17(5)(b)(ii)",
        ("club membership", "gym", "fitness", "health club", "membership"),
        (),
        "input tax credit on membership of a club health and fitness centre",
    ),
]


def _match_category(p: PurchaseEntry) -> _Category | None:
    text = " ".join(filter(None, [p.description, p.legal_name])).lower()
    hsn = (p.hsn_code or "").strip()
    for cat in CATEGORIES:
        if any(kw in text for kw in cat.keywords):
            return cat
        # HSN match for service categories (9963/9954) is a strong signal;
        # weak product HSNs (2106) only count alongside a keyword, handled above.
        if hsn and any(hsn.startswith(pre) for pre in cat.hsn_prefixes if pre in {"9963", "9954", "8703"}):
            return cat
    return None


def _pick_citation(citations: list[Citation], expected_section: str) -> Citation | None:
    for c in citations:
        if c.section.startswith(expected_section):
            return c
    return citations[0] if citations else None


def assess_itc_eligibility(
    purchases: list[PurchaseEntry],
    audit: AuditLog,
    kb: KnowledgeBase | None = None,
) -> dict:
    kb = kb or get_knowledge_base()
    blocked_value = 0.0
    eligible_value = 0.0
    uncertain = 0

    for p in purchases:
        cat = _match_category(p)
        if cat is None:
            p.itc_eligible = True
            eligible_value += p.total_tax
            continue

        result = kb.query(cat.query)
        citation = _pick_citation(result.citations, cat.expected_section)

        if not result.is_confident or citation is None:
            # Defer to human rather than assert a block on weak grounding.
            p.itc_eligible = None
            p.itc_block_reason = (
                f"Possible {cat.name} restriction — not certain. Please consult a CA."
            )
            uncertain += 1
            audit.record(
                agent=AGENT,
                entity_ref=p.invoice_number,
                decision="Uncertain — manual review",
                rationale=p.itc_block_reason,
                citation=citation,
                confident=False,
            )
            continue

        p.itc_eligible = False
        p.itc_block_reason = f"Blocked under {citation.section} ({cat.name})"
        p.citation = citation
        blocked_value += p.total_tax
        audit.record(
            agent=AGENT,
            entity_ref=p.invoice_number,
            decision=f"ITC BLOCKED — {citation.section}",
            rationale=f"{cat.name}: {p.description or p.legal_name}",
            citation=citation,
            confident=True,
        )

    return {
        "itc_blocked_value": round(blocked_value, 2),
        "itc_eligible_value": round(eligible_value, 2),
        "uncertain_count": uncertain,
    }
