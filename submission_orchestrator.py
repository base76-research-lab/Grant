from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


REQUIRED_PACK_FILES = ("abstract.md", "methodology.md", "impact.md", "references.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Autofill + validation orchestrator for grant submission")
    parser.add_argument("--output-dir", default="output", help="Grant output directory")
    parser.add_argument("--profile", default="research_profile.yaml", help="Path to researcher profile YAML")
    parser.add_argument(
        "--grant-id",
        default="",
        help="Grant ID to orchestrate; if omitted, latest generated meta file is used",
    )
    parser.add_argument(
        "--mode",
        choices=["dry-run", "human-gate"],
        default="dry-run",
        help="dry-run builds artifacts only; human-gate creates a final review checklist before manual submit",
    )
    parser.add_argument(
        "--orchestrator-out",
        default="output/submission_orchestrator",
        help="Directory for orchestrator artifacts",
    )
    return parser.parse_args()


def _load_profile(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data.get("researcher", {}) if isinstance(data, dict) else {}


def _find_meta_file(output_dir: Path, grant_id: str) -> Path:
    if grant_id:
        target = output_dir / f"{grant_id}_meta.json"
        if not target.exists():
            raise FileNotFoundError(f"Meta file not found for grant_id={grant_id}: {target}")
        return target

    candidates = sorted(output_dir.glob("*_meta.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError("No meta files found in output directory. Run run_pipeline.py first.")
    return candidates[0]


def _read_optional(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _first_paragraph(markdown_text: str) -> str:
    for block in markdown_text.split("\n\n"):
        cleaned = block.strip()
        if cleaned and not cleaned.startswith("#"):
            return cleaned
    return ""


def _build_field_map(meta: dict[str, Any], profile: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    grant_id = str(meta.get("grant_id", "")).strip()
    draft_text = _read_optional(output_dir / f"{grant_id}_draft.md")
    pack_dir = output_dir / "proposal_pack" / grant_id
    abstract = _read_optional(pack_dir / "abstract.md")
    methodology = _read_optional(pack_dir / "methodology.md")
    impact = _read_optional(pack_dir / "impact.md")
    references = _read_optional(pack_dir / "references.md")

    return {
        "grant_id": grant_id,
        "grant_title": meta.get("title", ""),
        "source": meta.get("source", ""),
        "deadline": meta.get("deadline", ""),
        "applicant_name": profile.get("name", ""),
        "institution": profile.get("institution", ""),
        "fields": profile.get("fields", []),
        "keywords": profile.get("keywords", []),
        "budget_range": profile.get("typical_budget", ""),
        "portal_form_map": {
            "project_title": meta.get("title", ""),
            "project_abstract": _first_paragraph(abstract) or _first_paragraph(draft_text),
            "methodology_summary": _first_paragraph(methodology),
            "impact_statement": _first_paragraph(impact),
            "references_summary": _first_paragraph(references),
            "applicant_organization": profile.get("institution", ""),
            "principal_investigator": profile.get("name", ""),
            "call_deadline": meta.get("deadline", ""),
        },
        "artifacts": {
            "draft": str(output_dir / f"{grant_id}_draft.md"),
            "checklist": str(output_dir / f"{grant_id}_submission_checklist.md"),
            "meta": str(output_dir / f"{grant_id}_meta.json"),
            "pack_dir": str(pack_dir),
        },
        "required_documents": meta.get("required_documents", []),
    }


def _validate(field_map: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    grant_id = field_map["grant_id"]
    portal = field_map["portal_form_map"]
    required_portal_fields = (
        "project_title",
        "project_abstract",
        "methodology_summary",
        "impact_statement",
        "applicant_organization",
        "principal_investigator",
    )

    missing_portal_fields = [name for name in required_portal_fields if not str(portal.get(name, "")).strip()]
    weak_fields = [
        name
        for name in ("project_abstract", "methodology_summary", "impact_statement")
        if len(str(portal.get(name, "")).strip()) < 40
    ]

    pack_dir = output_dir / "proposal_pack" / grant_id
    missing_pack_files = [name for name in REQUIRED_PACK_FILES if not (pack_dir / name).exists()]

    required_documents = [str(doc).strip().lower() for doc in (field_map.get("required_documents") or []) if str(doc).strip()]
    doc_presence = {
        "proposal": (output_dir / f"{grant_id}_proposal.md").exists(),
        "budget": (output_dir / f"{grant_id}_budget.md").exists(),
    }
    unresolved_required_documents = [doc for doc in required_documents if not doc_presence.get(doc, False)]

    is_ready = (
        not missing_portal_fields
        and not missing_pack_files
        and not weak_fields
        and not unresolved_required_documents
    )
    return {
        "grant_id": grant_id,
        "is_ready_for_human_submit": is_ready,
        "missing_portal_fields": missing_portal_fields,
        "weak_fields": weak_fields,
        "missing_pack_files": missing_pack_files,
        "unresolved_required_documents": unresolved_required_documents,
        "validated_at": datetime.now(UTC).isoformat(),
    }


def _write_human_gate_md(mode: str, field_map: dict[str, Any], validation: dict[str, Any], out_dir: Path) -> Path:
    grant_id = field_map["grant_id"]
    status = "READY" if validation["is_ready_for_human_submit"] else "BLOCKED"
    lines = [
        f"# Submission Orchestrator: {grant_id}",
        "",
        f"- Mode: `{mode}`",
        f"- Status: `{status}`",
        f"- Generated: `{datetime.now().isoformat(timespec='seconds')}`",
        "",
        "## Human Gate Checklist",
        "- [ ] Verify legal entity, signatory, and portal account context",
        "- [ ] Verify budget and attachments against call rules",
        "- [ ] Confirm no hallucinated claims in abstract/methodology/impact",
        "- [ ] Confirm final text and metadata",
        "- [ ] Human clicks submit in target portal",
        "",
        "## Validation Summary",
        f"- missing_portal_fields: `{len(validation['missing_portal_fields'])}`",
        f"- weak_fields: `{len(validation['weak_fields'])}`",
        f"- missing_pack_files: `{len(validation['missing_pack_files'])}`",
        f"- unresolved_required_documents: `{len(validation['unresolved_required_documents'])}`",
    ]

    if validation["missing_portal_fields"]:
        lines.append(f"- missing_portal_fields_list: `{', '.join(validation['missing_portal_fields'])}`")
    if validation["weak_fields"]:
        lines.append(f"- weak_fields_list: `{', '.join(validation['weak_fields'])}`")
    if validation["missing_pack_files"]:
        lines.append(f"- missing_pack_files_list: `{', '.join(validation['missing_pack_files'])}`")

    path = out_dir / f"{grant_id}_{mode}_review.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent
    output_dir = root / args.output_dir
    orchestrator_out = root / args.orchestrator_out
    orchestrator_out.mkdir(parents=True, exist_ok=True)

    profile = _load_profile(root / args.profile)
    meta_path = _find_meta_file(output_dir, args.grant_id.strip())
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    field_map = _build_field_map(meta, profile, output_dir)
    validation = _validate(field_map, output_dir)

    grant_id = field_map["grant_id"]
    field_map_path = orchestrator_out / f"{grant_id}_field_map.json"
    validation_path = orchestrator_out / f"{grant_id}_validation.json"
    review_path = _write_human_gate_md(args.mode, field_map, validation, orchestrator_out)

    field_map_path.write_text(json.dumps(field_map, indent=2), encoding="utf-8")
    validation_path.write_text(json.dumps(validation, indent=2), encoding="utf-8")

    print(f"Orchestrator mode: {args.mode}")
    print(f"Meta source: {meta_path}")
    print(f"Field map: {field_map_path}")
    print(f"Validation: {validation_path}")
    print(f"Human gate review: {review_path}")
    print(f"Ready for human submit: {validation['is_ready_for_human_submit']}")


if __name__ == "__main__":
    main()
