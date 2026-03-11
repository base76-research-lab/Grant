from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ResearchProfileIndex:
    profile: dict[str, Any]
    fields: list[str]
    keywords: list[str]
    assets: dict[str, list[str]]

    def as_text(self) -> str:
        parts: list[str] = []
        parts.extend(self.fields)
        parts.extend(self.keywords)
        for values in self.assets.values():
            parts.extend(values)
        return "\n".join([p for p in parts if p])


def load_profile_index(profile_file: Path) -> ResearchProfileIndex:
    with profile_file.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    profile = raw.get("researcher", {}) if isinstance(raw, dict) else {}
    fields = list(profile.get("fields", []) or [])
    keywords = list(profile.get("keywords", []) or [])

    assets_raw = profile.get("assets", {})
    assets: dict[str, list[str]] = {"papers": [], "repos": [], "experiments": []}
    if isinstance(assets_raw, dict):
        for key in assets:
            value = assets_raw.get(key, [])
            if isinstance(value, list):
                assets[key] = [str(v) for v in value if v]

    return ResearchProfileIndex(profile=profile, fields=fields, keywords=keywords, assets=assets)
