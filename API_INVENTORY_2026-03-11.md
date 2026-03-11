# Grant Agent API Inventory (2026-03-11)

## Implement Now (high confidence)

### 1) Vinnova Open Data (legacy APIs)
- Base: `https://data.vinnova.se/api/`
- Calls endpoint: `https://data.vinnova.se/api/utlysningar/{yyyy-mm-dd|diarienummer}`
- Example used: `https://data.vinnova.se/api/utlysningar/2019-09-01`
- Auth: none (public)
- Notes:
  - JSON includes title/description/publication date/doc links and application round IDs.
  - Good fit for discovery in EU/SE track.

### 2) Grants.gov REST API
- Base: `https://api.grants.gov`
- Search endpoint: `POST /v1/api/search2`
- Detail endpoint: `POST/GET fetchOpportunity` (as documented in API guide)
- Auth: none required for `search2` and `fetchOpportunity`
- Example payload:
  - `{"keyword":"AI","oppStatus":"forecasted|posted"}`
- Notes:
  - Returns token + `data.searchParams` + results.
  - Good low-friction external source for non-EU opportunities.

### 3) EU Funding & Tenders (SEDIA Search API)
- Endpoint: `POST https://api.tech.ec.europa.eu/search-api/prod/rest/search?apiKey=SEDIA&text=*`
- Content-Type: `application/json`
- Auth: uses public API key parameter (`SEDIA`) for public search use-cases.
- Query style: boolean filters in JSON body (`type`, `status`, programme filters).
- Notes:
  - `GET` returns 405, use `POST`.
  - Verified live with JSON payload and received results.

## Implement Next (medium confidence)

### 4) TED Developer APIs / TED Open Data
- Entry: `https://developer.ted.europa.eu/`
- Capabilities: search TED archives, eForms tooling, Open Data/SPARQL.
- Auth: depends on API family; developer signup/API key may be needed for some routes.
- Notes:
  - Valuable for procurement/tender signals, not pure grant calls.

### 5) NSF Award Search API
- Developer page links to Award Search API:
  - `https://resources.research.gov/common/webapi/awardapisearch-v1.htm`
- Notes:
  - Strong for historical award intelligence and funder pattern mining.
  - Useful for ranking/context enrichment.

## No clear public REST grants API found (for direct calls listing)

### Wellcome
- Public downloadable grant data exists (spreadsheets / 360Giving standard).
- Good source for dataset ingestion, but no single official public REST endpoint confirmed in this pass.

### Open Philanthropy (now Coefficient Giving branding)
- Public grants/funds pages available.
- No official public grants REST API confirmed in this pass.

### ESA Phi-lab / InCubed
- Open call information exists on web pages.
- No official public machine-friendly calls API confirmed in this pass.

## Recommended implementation order in GrantAgent

1. Add `vinnova_api` adapter (replace scraping path)
2. Add `grants_gov_api` adapter
3. Add `eu_ft_sedia_api` adapter with predefined query templates
4. Add `wellcome_dataset` loader (CSV/XLSX ingest)
5. Keep `openphilanthropy_web` and `esa_web` as scrape/manual until official APIs are confirmed
