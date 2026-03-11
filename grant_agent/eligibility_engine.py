from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml


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


DEFAULT_ELIGIBILITY_RULES: dict[str, Any] = {
    "topic": {
        "tokens": ["ai", "artificial", "interpretability", "governance", "uncertainty", "satellite"],
    },
    "weights": {
        "geo": 0.4,
        "budget": 0.25,
        "topic": 0.25,
        "deadline": 0.1,
    },
    "thresholds": {
        "eligible_min": 0.8,
    },
    "hard_fail": {
        "geo_mismatch": True,
        "deadline_passed": True,
    },
}


def load_eligibility_rules(path: Path | None) -> dict[str, Any]:
    """Load eligibility rule config from YAML file with safe defaults."""
    if path is None or not path.exists():
        return DEFAULT_ELIGIBILITY_RULES

    with path.open("r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}

    merged = dict(DEFAULT_ELIGIBILITY_RULES)
    for section in ["topic", "weights", "thresholds", "hard_fail"]:
        current = dict(DEFAULT_ELIGIBILITY_RULES.get(section, {}))
        override = loaded.get(section, {})
        if isinstance(override, dict):
            current.update(override)
        merged[section] = current
    return merged


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


def _parse_deadline(raw: str) -> date | None:
    if not raw or raw.lower() in {"rolling", "open"}:
        return None

    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"]:
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


def evaluate_grant_eligibility(
    profile: dict[str, Any],
    grant: dict[str, Any],
    rules: dict[str, Any] | None = None,
    today: date | None = None,
) -> EligibilityResult:
    now = today or date.today()
    cfg = rules or DEFAULT_ELIGIBILITY_RULES
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
    topic_tokens = cfg.get("topic", {}).get("tokens", [])
    if isinstance(topic_tokens, list) and topic_tokens:
        profile_terms = " ".join(profile.get("fields", []) + profile.get("keywords", [])).lower()
        grant_terms = " ".join([grant.get("title", ""), grant.get("description", "")] + grant.get("topic_keywords", [])).lower()
        topic_ok = any(str(token).lower() in profile_terms and str(token).lower() in grant_terms for token in topic_tokens)
    reasons.append("topic fit" if topic_ok else "weak topic fit")

    deadline_raw = str(grant.get("deadline", "")).strip()
    deadline_ok = True
    parsed_deadline = _parse_deadline(deadline_raw)
    if parsed_deadline is not None:
        deadline_ok = parsed_deadline >= now
    reasons.append("deadline valid" if deadline_ok else "deadline passed")

    hard_fail_geo = bool(cfg.get("hard_fail", {}).get("geo_mismatch", True)) and (not geo_ok)
    hard_fail_deadline = bool(cfg.get("hard_fail", {}).get("deadline_passed", True)) and (not deadline_ok)
    hard_fail = hard_fail_geo or hard_fail_deadline

    weights = cfg.get("weights", {}) if isinstance(cfg.get("weights"), dict) else {}
    w_geo = float(weights.get("geo", 0.4))
    w_budget = float(weights.get("budget", 0.25))
    w_topic = float(weights.get("topic", 0.25))
    w_deadline = float(weights.get("deadline", 0.1))

    base_score = 0.0
    base_score += w_geo if geo_ok else 0.0
    base_score += w_budget if budget_ok else 0.0
    base_score += w_topic if topic_ok else 0.0
    base_score += w_deadline if deadline_ok else 0.0

    eligible_min = float(cfg.get("thresholds", {}).get("eligible_min", 0.8))

    if hard_fail:
        status = "not_eligible"
    elif base_score >= eligible_min:
        status = "eligible"
    else:
        status = "maybe"

    return EligibilityResult(status=status, score=round(base_score, 3), reasons=reasons)
