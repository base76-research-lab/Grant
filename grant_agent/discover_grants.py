from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


@dataclass
class DiscoveryConfig:
    grants_file: Path
    geography: str | None = None
    max_results: int = 20
    source: str = "mock"
    vinnova_api_url: str = "https://data.vinnova.se/api/utlysningar/2024-01-01"
    grants_gov_api_url: str = "https://api.grants.gov/v1/api/search2"
    grants_gov_keyword: str = "artificial intelligence"
    eu_sedia_api_url: str = "https://api.tech.ec.europa.eu/search-api/prod/rest/search?apiKey=SEDIA&text=*"
    eu_sedia_text: str = "artificial intelligence"


def _parse_deadline(raw: str) -> date | None:
    if not raw or raw.lower() == "rolling":
        return None

    normalized = raw.strip()
    fmts = ["%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"]
    for fmt in fmts:
        try:
            return datetime.strptime(normalized, fmt).date()
        except ValueError:
            continue
    return None


def _geo_matches(required_geo: str, grant_geo: str) -> bool:
    req = required_geo.upper().strip()
    grant = grant_geo.upper().strip()
    if not grant:
        return False
    if grant in {"GLOBAL", req}:
        return True

    eu_members_or_assoc = {
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
    if req == "EU" and grant in eu_members_or_assoc:
        return True

    return False


def _fetch_json(url: str, method: str = "GET", payload: dict[str, Any] | None = None) -> Any:
    data = None
    headers = {"User-Agent": "GrantAgentMVP/0.1"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url, headers={"User-Agent": "GrantAgentMVP/0.1"})
    if method != "GET":
        req = Request(url, data=data, method=method, headers=headers)
    elif payload is not None:
        req = Request(url, data=data, method="POST", headers=headers)

    with urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def _discover_vinnova_api_grants(url: str, max_results: int) -> list[dict[str, Any]]:
    """Load Vinnova open data API and normalize records."""
    data = _fetch_json(url)
    if not isinstance(data, list):
        return []

    results: list[dict[str, Any]] = []
    for item in data[: max_results * 4]:
        if not isinstance(item, dict):
            continue

        dnr = str(item.get("Diarienummer", "")).strip()
        title = str(item.get("Titel", "")).strip() or str(item.get("TitelEngelska", "")).strip()
        if not dnr or not title:
            continue

        publication_date = str(item.get("Publiceringsdatum", "")).strip()
        description = str(item.get("Beskrivning", "")).strip() or "See call details"
        docs = item.get("DokumentLista") if isinstance(item.get("DokumentLista"), list) else []

        call_urls = []
        for doc in docs[:3]:
            if isinstance(doc, dict) and doc.get("fileURL"):
                call_urls.append(str(doc.get("fileURL")))

        short_desc = description.lower()
        topic_keywords = ["innovation", "research", "funding"]
        if "ai" in short_desc or "artificiell" in short_desc:
            topic_keywords.append("AI")
        if "digital" in short_desc:
            topic_keywords.append("digitalization")

        results.append(
            {
                "id": f"vinnova_api_{dnr.replace('-', '_')}",
                "source": "Vinnova",
                "title": title,
                "deadline": "rolling",
                "funding_amount_eur": 0,
                "geography": "SE",
                "eligibility": "See Vinnova call details",
                "required_documents": ["project_plan", "budget"],
                "topic_keywords": topic_keywords,
                "call_url": call_urls[0] if call_urls else "",
                "description": description,
                "publication_date": publication_date,
                "diarienummer": dnr,
                "discovery_source": "vinnova_api",
            }
        )

        if len(results) >= max_results:
            return results

    return results


def _discover_grants_gov_grants(url: str, max_results: int, keyword: str) -> list[dict[str, Any]]:
    """Load opportunities from Grants.gov search2 endpoint."""
    payload = {
        "keyword": keyword,
        "oppStatus": "forecasted|posted",
        "rows": max_results,
        "startRecordNum": 0,
    }
    data = _fetch_json(url, method="POST", payload=payload)
    if not isinstance(data, dict):
        return []

    body = data.get("data") if isinstance(data.get("data"), dict) else {}
    hits = body.get("oppHits") if isinstance(body.get("oppHits"), list) else []

    results: list[dict[str, Any]] = []
    for item in hits:
        if not isinstance(item, dict):
            continue

        opp_id = str(item.get("id", "")).strip()
        title = str(item.get("title", "")).strip()
        if not opp_id or not title:
            continue

        close_date = str(item.get("closeDate", "")).strip()
        agency = str(item.get("agency", "")).strip()
        agency_code = str(item.get("agencyCode", "")).strip()
        cfda_list = item.get("cfdaList") if isinstance(item.get("cfdaList"), list) else []

        topic_keywords = ["grant", "research", "federal"]
        title_l = title.lower()
        if "ai" in title_l or "artificial intelligence" in title_l:
            topic_keywords.append("AI")
        if "safety" in title_l:
            topic_keywords.append("AI safety")

        results.append(
            {
                "id": f"grantsgov_{opp_id}",
                "source": "Grants.gov",
                "title": title,
                "deadline": close_date if close_date else "rolling",
                "funding_amount_eur": 0,
                "geography": "GLOBAL",
                "eligibility": "See opportunity details",
                "required_documents": ["proposal", "budget"],
                "topic_keywords": topic_keywords,
                "call_url": f"https://www.grants.gov/search-results-detail/{opp_id}",
                "agency": agency,
                "agency_code": agency_code,
                "cfda_list": cfda_list,
                "discovery_source": "grants_gov_api",
            }
        )

    return results[:max_results]


def _discover_eu_sedia_grants(url: str, max_results: int, text: str) -> list[dict[str, Any]]:
    """Load opportunities from EU Funding & Tenders SEDIA API."""
    payload = {
        "query": text,
        "pageNumber": 0,
        "pageSize": max_results,
        "sortField": "relevance",
        "sortOrder": "DESC",
    }
    data = _fetch_json(url, method="POST", payload=payload)
    if not isinstance(data, dict):
        return []

    def _list_of_dicts(value: Any) -> bool:
        return isinstance(value, list) and value and all(isinstance(x, dict) for x in value)

    def _has_title_like(item: dict[str, Any]) -> bool:
        title_keys = {"title", "name", "subject", "callTitle", "topic", "identifier", "reference"}
        return any(k in item and str(item.get(k, "")).strip() for k in title_keys)

    def _collect_record_lists(node: Any, depth: int = 0) -> list[list[dict[str, Any]]]:
        if depth > 6:
            return []
        found: list[list[dict[str, Any]]] = []
        if _list_of_dicts(node):
            found.append(node)
        if isinstance(node, dict):
            for value in node.values():
                found.extend(_collect_record_lists(value, depth + 1))
        elif isinstance(node, list):
            for value in node:
                found.extend(_collect_record_lists(value, depth + 1))
        return found

    def _best_candidates(payload_obj: dict[str, Any]) -> list[dict[str, Any]]:
        lists = _collect_record_lists(payload_obj)
        if not lists:
            return []

        def score(lst: list[dict[str, Any]]) -> tuple[int, int]:
            title_like = sum(1 for item in lst[:50] if _has_title_like(item))
            return (title_like, len(lst))

        lists.sort(key=score, reverse=True)
        return lists[0]

    def _first_non_empty_str(item: dict[str, Any], keys: list[str]) -> str:
        for key in keys:
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, dict):
                for nested_key in ["value", "label", "name", "text", "title"]:
                    nested = value.get(nested_key)
                    if isinstance(nested, str) and nested.strip():
                        return nested.strip()
        return ""

    candidates = _best_candidates(data)

    results: list[dict[str, Any]] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue

        call_id = _first_non_empty_str(item, ["id", "reference", "callIdentifier", "identifier", "topicCode"])
        title = _first_non_empty_str(item, ["title", "name", "subject", "callTitle", "topic", "topicName"])
        if not title:
            continue
        if not call_id:
            call_id = f"sedia_{len(results)+1}"

        deadline = _first_non_empty_str(item, ["deadlineDate", "deadline", "closingDate", "endDate"]) or "rolling"

        description = _first_non_empty_str(item, ["description", "summary", "abstract", "teaser"])
        programme = _first_non_empty_str(item, ["programme", "programmeName", "frameworkProgramme"]) or "Horizon Europe"
        topic = _first_non_empty_str(item, ["topic", "topicName", "domain", "area"]) or "research"
        call_url = _first_non_empty_str(item, ["url", "link", "callUrl", "detailsUrl"])
        if not call_url:
            call_url = f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{call_id}"

        results.append(
            {
                "id": f"eu_sedia_{call_id.replace('/', '_').replace(' ', '_')}",
                "source": "EU Funding & Tenders",
                "title": title,
                "deadline": deadline,
                "funding_amount_eur": 0,
                "geography": "EU",
                "eligibility": "See call eligibility conditions",
                "required_documents": ["proposal", "budget", "consortium_info"],
                "topic_keywords": [programme, topic, text, "research", "funding"],
                "call_url": call_url,
                "description": description,
                "programme": programme,
                "topic": topic,
                "discovery_source": "eu_sedia_api",
            }
        )

        if len(results) >= max_results:
            return results

    return results


def _discover_mock_grants(grants_file: Path) -> list[dict[str, Any]]:
    with grants_file.open("r", encoding="utf-8") as f:
        grants = json.load(f)
    for grant in grants:
        grant.setdefault("discovery_source", "mock")
    return grants


def discover_grants(config: DiscoveryConfig) -> list[dict[str, Any]]:
    """Load grants from configured source and apply lightweight filters."""
    if config.source == "vinnova_api":
        try:
            grants = _discover_vinnova_api_grants(config.vinnova_api_url, config.max_results)
            if not grants:
                grants = _discover_mock_grants(config.grants_file)
                for grant in grants:
                    grant["discovery_source"] = "mock_fallback_vinnova_api"
        except (URLError, TimeoutError, ValueError):
            grants = _discover_mock_grants(config.grants_file)
            for grant in grants:
                grant["discovery_source"] = "mock_fallback_vinnova_api"
    elif config.source == "grants_gov_api":
        try:
            grants = _discover_grants_gov_grants(
                config.grants_gov_api_url, config.max_results, config.grants_gov_keyword
            )
            if not grants:
                grants = _discover_mock_grants(config.grants_file)
                for grant in grants:
                    grant["discovery_source"] = "mock_fallback_grants_gov_api"
        except (URLError, TimeoutError, ValueError):
            grants = _discover_mock_grants(config.grants_file)
            for grant in grants:
                grant["discovery_source"] = "mock_fallback_grants_gov_api"
    elif config.source == "eu_sedia_api":
        try:
            grants = _discover_eu_sedia_grants(config.eu_sedia_api_url, config.max_results, config.eu_sedia_text)
            if not grants:
                grants = _discover_mock_grants(config.grants_file)
                for grant in grants:
                    grant["discovery_source"] = "mock_fallback_eu_sedia_api"
        except (URLError, TimeoutError, ValueError):
            grants = _discover_mock_grants(config.grants_file)
            for grant in grants:
                grant["discovery_source"] = "mock_fallback_eu_sedia_api"
    else:
        grants = _discover_mock_grants(config.grants_file)

    out: list[dict[str, Any]] = []
    for grant in grants:
        if config.geography:
            grant_geo = (grant.get("geography") or "").upper()
            req_geo = config.geography.upper()
            if not _geo_matches(req_geo, grant_geo):
                continue

        deadline = _parse_deadline(str(grant.get("deadline", "")))
        grant["deadline_sort"] = deadline.isoformat() if deadline else "9999-12-31"
        out.append(grant)

    out.sort(key=lambda g: g["deadline_sort"])
    return out[: config.max_results]
