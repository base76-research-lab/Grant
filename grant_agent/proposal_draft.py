from __future__ import annotations

from pathlib import Path
from typing import Any


def _pick_template(grant: dict[str, Any], templates_dir: Path) -> Path:
    source = (grant.get("source") or "").lower()
    if "esa" in source:
        return templates_dir / "esa.md"
    if "erc" in source:
        return templates_dir / "erc.md"
    return templates_dir / "horizon_europe.md"


def _build_sections(grant: dict[str, Any], researcher: dict[str, Any]) -> dict[str, str]:
    name = researcher.get("name", "The applicant")
    institution = researcher.get("institution", "the institution")
    fields = ", ".join(researcher.get("fields", []))

    title = grant.get("title", "this call")
    abstract = (
        f"{name} at {institution} proposes a targeted program for {title}. "
        f"The work operationalizes {fields} into an auditable research stack with explicit uncertainty controls."
    )
    objectives = (
        "1) Build reproducible observability metrics. "
        "2) Validate reliability gains with pre-registered evaluation. "
        "3) Deliver open technical artifacts and policy-facing summaries."
    )
    methodology = (
        "We combine mechanistic analysis, controlled ablations, and risk-gated interventions. "
        "All runs are logged with trace IDs, decision metadata, and benchmark deltas for auditability."
    )
    impact = (
        "Expected impact is lower operational risk in AI-supported decision pipelines, "
        "faster validation cycles, and improved trust through transparent evidence."
    )
    budget = (
        "Budget is allocated to researcher time, compute, evaluation infrastructure, "
        "and dissemination. Cost lines map directly to milestones and measurable outputs."
    )
    timeline = "M1-M2 setup, M3-M5 experiments, M6 validation and publication package."

    return {
        "abstract": abstract,
        "objectives": objectives,
        "methodology": methodology,
        "impact": impact,
        "budget": budget,
        "timeline": timeline,
    }


def generate_draft(grant: dict[str, Any], researcher: dict[str, Any], templates_dir: Path) -> str:
    template_path = _pick_template(grant, templates_dir)
    template = template_path.read_text(encoding="utf-8")
    sections = _build_sections(grant, researcher)
    return template.format(**sections)
