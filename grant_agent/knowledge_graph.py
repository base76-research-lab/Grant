from __future__ import annotations

from typing import Any

from grant_agent.profile_index import ResearchProfileIndex


def _grant_node(grant: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(grant.get("id", "")),
        "type": "Grant",
        "agency": grant.get("source", "unknown"),
        "program": grant.get("programme") or grant.get("agency") or "unknown",
        "topic": grant.get("topic") or ", ".join(grant.get("topic_keywords", [])),
        "budget": grant.get("funding_amount_eur", 0),
        "eligibility": grant.get("eligibility", "See call"),
        "deadline": grant.get("deadline", "rolling"),
    }


def build_knowledge_graph(grants: list[dict[str, Any]], profile_index: ResearchProfileIndex) -> dict[str, Any]:
    """Build a lightweight graph connecting profile terms to grants."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    profile_node_id = "research_profile"
    nodes.append(
        {
            "id": profile_node_id,
            "type": "ResearchProfile",
            "fields": profile_index.fields,
            "keywords": profile_index.keywords,
            "assets": profile_index.assets,
        }
    )

    for grant in grants:
        g_node = _grant_node(grant)
        nodes.append(g_node)
        edges.append(
            {
                "source": profile_node_id,
                "target": g_node["id"],
                "relation": "potential_match",
                "via": grant.get("discovery_source", "unknown"),
            }
        )

        for kw in grant.get("topic_keywords", []):
            kw_id = f"topic::{str(kw).strip().lower().replace(' ', '_')}"
            if not any(n.get("id") == kw_id for n in nodes):
                nodes.append({"id": kw_id, "type": "Topic", "label": kw})
            edges.append({"source": g_node["id"], "target": kw_id, "relation": "has_topic"})

    return {"nodes": nodes, "edges": edges}
