from __future__ import annotations

import argparse
import json
from pathlib import Path

from grant_agent.discover_grants import DiscoveryConfig, discover_grants
from grant_agent.eligibility_engine import load_eligibility_rules
from grant_agent.proposal_draft import generate_draft
from grant_agent.rank_grants import load_research_profile, rank_grants
from grant_agent.submission_helper import create_submission_packet


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

    profile = load_research_profile(root / args.profile)
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
        return

    draft_text = generate_draft(approved_grant, profile, root / args.templates)
    packet = create_submission_packet(approved_grant, draft_text, root / args.out)

    print("\nDraft package created (human review gate):")
    print(f"- Approval source: {approval_source}")
    print(f"- Draft: {packet['draft_file']}")
    print(f"- Checklist: {packet['checklist_file']}")
    print(f"- Meta: {packet['meta_file']}")


if __name__ == "__main__":
    main()
