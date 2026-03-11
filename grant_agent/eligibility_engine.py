from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


EU_MEMBERS_OR_ASSOC = {
    "SE",
    "FI",
    "DK",
    "NO",
    "IS",
    "DE",
    "FR",
    "NL",
    "BE",
    "LU",
    "AT",
    "IE",
    "IT",
    "ES",
    "PT",
    "PL",
    "CZ",
    "SK",
    "SI",
    "HR",
    "HU",
    "RO",
    "BG",
    "GR",
    "CY",
    "MT",
    "EE",
    "LV",
    "LT",
}


@dataclass
class EligibilityResult:
    status: str
    score: float
    reasons: list[str]


def _parse_budget_range(raw: str) -> tuple[int, int]:
    budget_min, budget_max = 0, 10**12
    try:
        numeric = "".join(ch if ch.isdigit() or ch == "-" else " " for ch in str(raw))
        parts = [int(p) for p in numeric.split() if p.isdigit()]
        if len(parts) >= 2:
            budget_min, budget_max = parts[0], parts[1]
    except Exception:
        pass
    return budget_min, budget_max


def _geo_match(required_geo: str, grant_geo: str) -> bool:
    req = required_geo.upper().strip()
    geo = grant_geo.upper().strip()
    if not req:
        return True
    if geo in {"GLOBAL", req}:
        return True
    if req == "EU" and geo in EU_MEMBERS_OR_ASSOC:
        return True
    return False


def _topic_fit(profile: dict[str, Any], grant: dict[str, Any]) -> bool:
    profile_terms = " ".join(profile.get("fields", []) + profile.get("keywords", [])).lower()
    grant_terms = " ".join([grant.get("title", ""), grant.get("description", "")] + grant.get("topic_keywords", [])).lower()

    for token in ["ai", "artificial", "interpretability", "governance", "uncertainty", "satellite"]:
        if token in profile_terms and token in grant_terms:
            return True
    return False


def evaluate_grant_eligibility(profile: dict[str, Any], grant: dict[str, Any], today: date | None = None) -> EligibilityResult:
    now = today or date.today()
    reasons: list[str] = []

    geo_req = str(profile.get("geography", "")).upper()
    grant_geo = str(grant.get("geography", "")).upper()
    geo_ok = _geo_match(geo_req, grant_geo)
    reasons.append("geography match" if geo_ok else "geography mismatch")

    budget_min, budget_max = _parse_budget_range(profile.get("typical_budget", ""))
    amount = int(grant.get("funding_amount_eur", 0) or 0)
    budget_ok = amount == 0 or budget_min <= amount <= budget_max
    reasons.append("budget fit" if budget_ok else "budget outside preferred range")

    topic_ok = _topic_fit(profile, grant)
    reasons.append("topic fit" if topic_ok else "weak topic fit")

    deadline_raw = str(grant.get("deadline", "")).strip().lower()
    deadline_ok = True
    if deadline_raw and deadline_raw not in {"rolling", "open"}:
        # Conservative check for ISO-only dates; non-ISO is treated as unknown and not rejected.
        try:
            year, month, day = [int(x) for x in deadline_raw.split("-")[:3]]
            deadline_ok = date(year, month, day) >= now
        except Exception:
            deadline_ok = True
    reasons.append("deadline valid" if deadline_ok else "deadline passed")

    hard_fail = not geo_ok or not deadline_ok
    base_score = 0.0
    base_score += 0.4 if geo_ok else 0.0
    base_score += 0.25 if budget_ok else 0.0
    base_score += 0.25 if topic_ok else 0.0
    base_score += 0.1 if deadline_ok else 0.0

    if hard_fail:
        status = "not_eligible"
    elif base_score >= 0.8:
        status = "eligible"
    else:
        status = "maybe"

    return EligibilityResult(status=status, score=round(base_score, 3), reasons=reasons)
