from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import re

import yaml

from grant_agent.eligibility_engine import evaluate_grant_eligibility


@dataclass
class RankedGrant:
    grant: dict[str, Any]
    match_score: float
    eligibility_status: str
    eligibility_score: float
    reasons: list[str]


def load_research_profile(profile_file: Path) -> dict[str, Any]:
    with profile_file.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return raw["researcher"]


def _norm_set(items: list[str]) -> set[str]:
    return {x.strip().lower() for x in items if x and x.strip()}


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if t}


def rank_grants(
    grants: list[dict[str, Any]],
    profile: dict[str, Any],
    eligibility_rules: dict[str, Any] | None = None,
) -> list[RankedGrant]:
    fields = _norm_set(profile.get("fields", []))
    keywords = _norm_set(profile.get("keywords", []))
    all_profile_terms = fields | keywords

    budget_raw = str(profile.get("typical_budget", ""))
    budget_min, budget_max = 0, 10**12
    try:
        numeric = "".join(ch if ch.isdigit() or ch == "-" else " " for ch in budget_raw)
        parts = [int(p) for p in numeric.split() if p.isdigit()]
        if len(parts) >= 2:
            budget_min, budget_max = parts[0], parts[1]
    except Exception:
        pass

    preferred_geo = str(profile.get("geography", "")).upper()

    ranked: list[RankedGrant] = []
    for grant in grants:
        eligibility = evaluate_grant_eligibility(profile, grant, rules=eligibility_rules)

        topic_terms = _norm_set(grant.get("topic_keywords", []))
        topic_tokens: set[str] = set()
        for term in topic_terms:
            topic_tokens |= _tokens(term)

        matched_profile_terms: set[str] = set()
        for term in all_profile_terms:
            if _tokens(term) & topic_tokens:
                matched_profile_terms.add(term)

        overlap_score = min(len(matched_profile_terms) / max(len(all_profile_terms), 1), 1.0)

        amount = int(grant.get("funding_amount_eur", 0) or 0)
        budget_ok = 1.0 if budget_min <= amount <= budget_max else 0.5

        geo = str(grant.get("geography", "")).upper()
        geo_ok = 1.0 if geo in {"GLOBAL", preferred_geo} else 0.4

        score = 0.45 * overlap_score + 0.2 * budget_ok + 0.1 * geo_ok + 0.25 * eligibility.score

        reasons: list[str] = []
        for term in sorted(matched_profile_terms):
            reasons.append(f"+ {term}")
        if budget_ok >= 1.0:
            reasons.append("+ budget fit")
        if geo_ok >= 1.0:
            reasons.append("+ geography fit")
        reasons.append(f"+ eligibility={eligibility.status} ({eligibility.score:.2f})")
        for item in eligibility.reasons[:2]:
            reasons.append(f"+ {item}")

        ranked.append(
            RankedGrant(
                grant=grant,
                match_score=round(score, 3),
                eligibility_status=eligibility.status,
                eligibility_score=eligibility.score,
                reasons=reasons,
            )
        )

    ranked.sort(key=lambda x: x.match_score, reverse=True)
    return ranked
