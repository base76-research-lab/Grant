from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def create_submission_packet(grant: dict[str, Any], draft_text: str, out_dir: Path) -> dict[str, Any]:
    """Create a human-review package instead of auto-submitting."""
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = str(grant.get("id", "grant")).strip().replace(" ", "_")

    draft_file = out_dir / f"{slug}_draft.md"
    checklist_file = out_dir / f"{slug}_submission_checklist.md"
    meta_file = out_dir / f"{slug}_meta.json"

    draft_file.write_text(draft_text, encoding="utf-8")

    checklist = [
        f"# Submission Checklist: {grant.get('title', '')}",
        "",
        "- [ ] Eligibility validated manually",
        "- [ ] Budget lines verified against call rules",
        "- [ ] Required attachments uploaded",
        "- [ ] Final text reviewed by PI",
        "- [ ] Submit button clicked by human",
    ]
    checklist_file.write_text("\n".join(checklist), encoding="utf-8")

    meta = {
        "grant_id": grant.get("id"),
        "source": grant.get("source"),
        "title": grant.get("title"),
        "deadline": grant.get("deadline"),
        "required_documents": grant.get("required_documents", []),
        "status": "ready_for_human_submission",
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return {
        "draft_file": str(draft_file),
        "checklist_file": str(checklist_file),
        "meta_file": str(meta_file),
    }
