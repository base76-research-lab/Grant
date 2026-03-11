from __future__ import annotations

from pathlib import Path
from typing import Any

from grant_agent.profile_index import ResearchProfileIndex


def _join_lines(lines: list[str]) -> str:
    return "\n".join(lines).strip() + "\n"


def build_evidence_pack(grant: dict[str, Any], profile_index: ResearchProfileIndex, out_dir: Path) -> dict[str, str]:
    """Create a structured proposal evidence pack for a selected grant."""
    slug = str(grant.get("id", "grant")).replace(" ", "_")
    pack_dir = out_dir / "proposal_pack" / slug
    pack_dir.mkdir(parents=True, exist_ok=True)

    title = str(grant.get("title", "Research Grant"))
    fields = ", ".join(profile_index.fields)

    abstract = _join_lines(
        [
            f"# Abstract: {title}",
            "",
            f"This proposal targets {title} with a research program focused on {fields}.",
            "The evidence strategy combines prior publications, code assets, and experiment logs.",
        ]
    )
    methodology = _join_lines(
        [
            f"# Methodology: {title}",
            "",
            "- Define measurable hypotheses and pre-registered criteria.",
            "- Execute experiments in reproducible pipelines with trace metadata.",
            "- Validate outcomes against reliability, safety, and interpretability metrics.",
        ]
    )
    impact = _join_lines(
        [
            f"# Impact: {title}",
            "",
            "Expected outcomes:",
            "- Stronger evidence quality for AI research decisions",
            "- Faster translation from experiment to publication",
            "- More competitive and auditable grant submissions",
        ]
    )

    refs: list[str] = [f"# References: {title}", ""]
    refs.append("## Papers")
    refs.extend([f"- {item}" for item in profile_index.assets.get("papers", [])] or ["- (add papers)"])
    refs.append("")
    refs.append("## Repositories")
    refs.extend([f"- {item}" for item in profile_index.assets.get("repos", [])] or ["- (add repositories)"])
    refs.append("")
    refs.append("## Experiments")
    refs.extend([f"- {item}" for item in profile_index.assets.get("experiments", [])] or ["- (add experiments)"])
    references = _join_lines(refs)

    files = {
        "abstract": pack_dir / "abstract.md",
        "methodology": pack_dir / "methodology.md",
        "impact": pack_dir / "impact.md",
        "references": pack_dir / "references.md",
    }
    files["abstract"].write_text(abstract, encoding="utf-8")
    files["methodology"].write_text(methodology, encoding="utf-8")
    files["impact"].write_text(impact, encoding="utf-8")
    files["references"].write_text(references, encoding="utf-8")

    return {k: str(v) for k, v in files.items()}
