from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from config.auth_config import load_auth_config, validate_auth_config
from grant_agent.discover_grants import DiscoveryConfig, discover_grants
from grant_agent.evidence_pack_builder import build_evidence_pack
from grant_agent.eligibility_engine import load_eligibility_rules
from grant_agent.knowledge_graph import build_knowledge_graph
from grant_agent.profile_index import load_profile_index
from grant_agent.proposal_draft import generate_draft
from grant_agent.rank_grants import load_research_profile, rank_grants
from grant_agent.submission_helper import create_submission_packet


def _resolve_grant_url(grant: dict) -> str:
    """Return best-effort canonical URL for a grant record."""
    for key in ("url", "call_url", "details_url", "link"):
        value = grant.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    grant_id = str(grant.get("id", "")).strip()
    source = str(grant.get("source", "")).lower()
    discovery_source = str(grant.get("discovery_source", "")).lower()

    if "grants.gov" in source or "grants_gov" in discovery_source or grant_id.startswith("grantsgov_"):
        opp_id = grant_id.replace("grantsgov_", "")
        if opp_id:
            return f"https://www.grants.gov/search-results-detail/{opp_id}"

    if "eu funding" in source or "sedia" in discovery_source or grant_id.startswith("eu_sedia_"):
        call_id = grant_id.replace("eu_sedia_", "")
        if call_id:
            return (
                "https://ec.europa.eu/info/funding-tenders/opportunities/portal/"
                f"screen/opportunities/topic-details/{call_id}"
            )

    if "vinnova" in source or "vinnova" in discovery_source or grant_id.startswith("vinnova"):
        return "https://www.vinnova.se/"

    if "esa" in source or grant_id.startswith("esa_"):
        return "https://phi.esa.int/"

    if "erc" in source or grant_id.startswith("erc_"):
        return "https://erc.europa.eu/"

    if "open philanthropy" in source or grant_id.startswith("open_phil"):
        return "https://www.openphilanthropy.org/"

    return ""


def _count_ready_packages(out_dir: Path) -> int:
    proposal_pack_dir = out_dir / "proposal_pack"
    required_files = ("abstract.md", "methodology.md", "impact.md", "references.md")

    if not proposal_pack_dir.exists():
        return 0

    ready_count = 0
    for grant_dir in proposal_pack_dir.iterdir():
        if grant_dir.is_dir() and all((grant_dir / name).exists() for name in required_files):
            ready_count += 1
    return ready_count


def _write_dod_scorecard(ranked_payload: list[dict], out_dir: Path) -> Path:
    total = len(ranked_payload)
    complete = sum(
        1
        for item in ranked_payload
        if all(str(item.get(key, "")).strip() for key in ("title", "deadline", "source", "url"))
    )
    coverage_rate = (complete / total) if total else 0.0

    top3 = ranked_payload[:3]
    relevant_top3 = sum(
        1
        for item in top3
        if str(item.get("eligibility_status", "")).lower() in {"eligible", "maybe"}
        and float(item.get("match_score", 0) or 0) >= 0.6
    )
    top3_precision = (relevant_top3 / 3) if len(top3) == 3 else 0.0
    ready_package_count = _count_ready_packages(out_dir)

    scorecard_lines = [
        "# Grant DoD Scorecard",
        "",
        f"- Generated: {datetime.now().isoformat(timespec='seconds')}",
        "- Data source: `output/ranked_grants.json` + `output/proposal_pack/`",
        "",
        "## Metrics",
        f"- coverage_rate: `{coverage_rate:.3f}` ({complete}/{total})",
        f"- top3_precision: `{top3_precision:.3f}` ({relevant_top3}/3)",
        f"- ready_package_count: `{ready_package_count}`",
        "",
        "## Status",
        f"- Discovery/ranking: {'GREEN' if coverage_rate == 1.0 and top3_precision == 1.0 else 'YELLOW'}",
        f"- Package readiness: {'GREEN' if ready_package_count >= 1 else 'YELLOW'}",
        f"- Schema completeness (url): {'GREEN' if coverage_rate == 1.0 else 'YELLOW'}",
        "",
        "## Next Action (single)",
        "- Keep these three metrics green for two consecutive non-mock runs before adding new features.",
    ]

    scorecard_path = out_dir / "DoD_SCORECARD.md"
    scorecard_path.parent.mkdir(parents=True, exist_ok=True)
    scorecard_path.write_text("\n".join(scorecard_lines) + "\n", encoding="utf-8")
    return scorecard_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Grant Agent MVP pipeline")
    parser.add_argument("--profile", default="research_profile.yaml", help="Path to researcher profile YAML")
    parser.add_argument("--grants", default="data/mock_grants.json", help="Path to grants JSON")
    parser.add_argument(
        "--discovery-source",
        choices=["mock", "vinnova_api", "grants_gov_api", "eu_sedia_api"],
        default="mock",
        help="Grant discovery source",
    )
    parser.add_argument(
        "--vinnova-api-url",
        default="https://data.vinnova.se/api/utlysningar/2024-01-01",
        help="Vinnova API URL for discovery",
    )
    parser.add_argument(
        "--grants-gov-api-url",
        default="https://api.grants.gov/v1/api/search2",
        help="Grants.gov search API URL for discovery",
    )
    parser.add_argument(
        "--grants-gov-keyword",
        default="artificial intelligence",
        help="Keyword used when querying Grants.gov",
    )
    parser.add_argument(
        "--eu-sedia-api-url",
        default="https://api.tech.ec.europa.eu/search-api/prod/rest/search?apiKey=SEDIA&text=*",
        help="EU SEDIA search API URL for discovery",
    )
    parser.add_argument(
        "--eu-sedia-text",
        default="artificial intelligence",
        help="Query text used when querying EU SEDIA",
    )
    parser.add_argument("--templates", default="templates", help="Directory with proposal templates")
    parser.add_argument("--out", default="output", help="Output directory")
    parser.add_argument("--top-k", type=int, default=3, help="How many grants to rank")
    parser.add_argument("--approve-rank", type=int, default=0, help="Approve grant by rank index (1-based)")
    parser.add_argument("--approve-grant-id", default="", help="Approve grant by explicit grant ID")
    parser.add_argument("--auto-approve-top", action="store_true", help="Auto-approve top-ranked grant")
    parser.add_argument(
        "--ranked-output",
        default="output/ranked_grants.json",
        help="Where to write ranked grants JSON report",
    )
    parser.add_argument(
        "--eligibility-rules",
        default="eligibility_rules.yaml",
        help="Path to YAML file with eligibility rules",
    )
    parser.add_argument(
        "--knowledge-graph-output",
        default="output/grant_knowledge_graph.json",
        help="Where to write grant knowledge graph JSON",
    )
    parser.add_argument(
        "--auth-env-file",
        default=".env",
        help="Path to env file containing auth settings",
    )
    return parser.parse_args()


def _select_approved_grant(ranked, approve_rank: int, approve_grant_id: str, auto_approve_top: bool):
    if approve_grant_id:
        for item in ranked:
            if str(item.grant.get("id", "")) == approve_grant_id:
                return item.grant, f"grant_id={approve_grant_id}"
        return None, f"grant_id={approve_grant_id} not found"

    if approve_rank > 0:
        idx = approve_rank - 1
        if 0 <= idx < len(ranked):
            return ranked[idx].grant, f"rank={approve_rank}"
        return None, f"rank={approve_rank} out of range"

    if auto_approve_top and ranked:
        return ranked[0].grant, "auto_approve_top"

    return None, "no_approval"


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent

    auth_config = load_auth_config(root / args.auth_env_file)
    auth_warnings = validate_auth_config(auth_config)
    print(
        f"Auth context: mode={auth_config.auth_mode}, tenant_mode={auth_config.tenant_mode}, user_id={auth_config.user_id}"
    )
    for warning in auth_warnings:
        print(f"Auth warning: {warning}")

    profile_path = root / args.profile
    profile = load_research_profile(profile_path)
    profile_index = load_profile_index(profile_path)
    eligibility_rules = load_eligibility_rules(root / args.eligibility_rules)
    discovered = discover_grants(
        DiscoveryConfig(
            grants_file=root / args.grants,
            geography=profile.get("geography"),
            max_results=50,
            source=args.discovery_source,
            vinnova_api_url=args.vinnova_api_url,
            grants_gov_api_url=args.grants_gov_api_url,
            grants_gov_keyword=args.grants_gov_keyword,
            eu_sedia_api_url=args.eu_sedia_api_url,
            eu_sedia_text=args.eu_sedia_text,
        )
    )

    graph = build_knowledge_graph(discovered, profile_index)
    graph_output_path = root / args.knowledge_graph_output
    graph_output_path.parent.mkdir(parents=True, exist_ok=True)
    graph_output_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    print(f"Knowledge graph exported: {graph_output_path}")

    ranked = rank_grants(discovered, profile, eligibility_rules=eligibility_rules)[: args.top_k]

    print("\nTop matched grants:")
    for idx, item in enumerate(ranked, start=1):
        grant = item.grant
        print(
            f"{idx}. {grant['title']} | score={item.match_score:.3f} "
            f"| deadline={grant['deadline']} | source={grant.get('discovery_source', 'unknown')}"
        )
        for reason in item.reasons[:4]:
            print(f"   {reason}")

    if not ranked:
        print("\nNo matching grants found.")
        scorecard_path = _write_dod_scorecard([], root / args.out)
        print(f"DoD scorecard updated: {scorecard_path}")
        return

    ranked_payload = []
    for idx, item in enumerate(ranked, start=1):
        ranked_payload.append(
            {
                "rank": idx,
                "grant_id": item.grant.get("id"),
                "title": item.grant.get("title"),
                "source": item.grant.get("source"),
                "discovery_source": item.grant.get("discovery_source", "unknown"),
                "url": _resolve_grant_url(item.grant),
                "deadline": item.grant.get("deadline"),
                "match_score": item.match_score,
                "eligibility_status": item.eligibility_status,
                "eligibility_score": item.eligibility_score,
                "reasons": item.reasons,
            }
        )

    ranked_output_path = root / args.ranked_output
    ranked_output_path.parent.mkdir(parents=True, exist_ok=True)
    ranked_output_path.write_text(json.dumps(ranked_payload, indent=2), encoding="utf-8")
    print(f"\nRanked grants exported: {ranked_output_path}")

    approved_grant, approval_source = _select_approved_grant(
        ranked, args.approve_rank, args.approve_grant_id.strip(), args.auto_approve_top
    )

    if not approved_grant:
        print("\nNo approved grant selected yet.")
        print("Re-run with one of:")
        print("- --approve-rank 1")
        print("- --approve-grant-id <grant_id>")
        print("- --auto-approve-top")
        if approval_source not in {"no_approval"}:
            print(f"Approval note: {approval_source}")
        scorecard_path = _write_dod_scorecard(ranked_payload, root / args.out)
        print(f"DoD scorecard updated: {scorecard_path}")
        return

    draft_text = generate_draft(approved_grant, profile, root / args.templates)
    packet = create_submission_packet(approved_grant, draft_text, root / args.out)
    evidence_pack = build_evidence_pack(approved_grant, profile_index, root / args.out)

    print("\nDraft package created (human review gate):")
    print(f"- Approval source: {approval_source}")
    print(f"- Draft: {packet['draft_file']}")
    print(f"- Checklist: {packet['checklist_file']}")
    print(f"- Meta: {packet['meta_file']}")
    print(f"- Evidence abstract: {evidence_pack['abstract']}")
    print(f"- Evidence methodology: {evidence_pack['methodology']}")
    print(f"- Evidence impact: {evidence_pack['impact']}")
    print(f"- Evidence references: {evidence_pack['references']}")

    scorecard_path = _write_dod_scorecard(ranked_payload, root / args.out)
    print(f"DoD scorecard updated: {scorecard_path}")


if __name__ == "__main__":
    main()
