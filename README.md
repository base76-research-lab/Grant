# Grant

<p align="center">
	<img src="assets/grant-logo.png" alt="Grant logo" width="220" />
</p>

Grant is an AI agent that helps researchers find and apply for research funding.

## Landing Pitch

Grant cuts funding search and first-draft work from hours to minutes for AI researchers.

- Problem: funding discovery is fragmented and proposal starts are cognitively expensive.
- Solution: one command to discover calls, rank relevance, and generate a human-review proposal pack.
- Outcome: less admin friction, faster decision cycles, more time for research.

## What Grant Does

- Discovers funding opportunities from relevant grant sources
- Ranks opportunities against a researcher or lab profile
- Generates structured proposal drafts
- Produces submission-ready checklists and metadata for human review
- Evaluates baseline eligibility (`eligible`, `maybe`, `not_eligible`) with explainable reasons
- Builds a grant knowledge graph for machine-readable matching
- Builds an evidence pack (`abstract`, `methodology`, `impact`, `references`) for matched grants

## Product Positioning

Grant is an AI funding copilot, not an autonomous submitter.
Final decisions and submission actions remain under human control.

## Core Workflow

`discover -> rank -> draft -> submission-ready package`

## Autonomous Research Infrastructure

Grant is designed to plug into a broader research loop:

`Research OS -> Grant Agent -> Experiment Pipeline -> Publication Packaging`

Resulting cycle:

`idea -> experiment -> paper -> grant -> funding -> larger experiment`

## Discovery Sources

- `mock`
- `vinnova_api`
- `grants_gov_api`
- `eu_sedia_api`

## Auth Per User

Grant supports per-user operation via API key mode now and OAuth-ready mode.

1. Copy `.env.example` to `.env`.
2. Set `GRANT_AUTH_MODE=api_key` (default) or `GRANT_AUTH_MODE=oauth`.
3. Run pipeline with optional auth env path:

```bash
python3 run_pipeline.py --auth-env-file .env --top-k 3
```

See `AUTH_MODEL.md` for the full model.

## Run

```bash
python3 run_pipeline.py --top-k 3
python3 run_pipeline.py --discovery-source eu_sedia_api --eu-sedia-text "artificial intelligence"
```

Use custom eligibility rules:

```bash
python3 run_pipeline.py --eligibility-rules eligibility_rules.yaml
```

Outputs now include:

- `output/grant_knowledge_graph.json`
- `output/proposal_pack/<grant_id>/abstract.md`
- `output/proposal_pack/<grant_id>/methodology.md`
- `output/proposal_pack/<grant_id>/impact.md`
- `output/proposal_pack/<grant_id>/references.md`

## 60-Second Demo

Run a live discovery + auto-approval flow and review generated artifacts:

```bash
python3 run_pipeline.py \
	--discovery-source grants_gov_api \
	--grants-gov-keyword "artificial intelligence" \
	--top-k 1 \
	--auto-approve-top \
	--auth-env-file .env
```

Demo artifacts to show in a GIF/video:

- Ranked output: `output/ranked_grants.json`
- Draft: `output/<grant_id>_draft.md`
- Checklist: `output/<grant_id>_submission_checklist.md`
- Proposal pack: `output/proposal_pack/<grant_id>/`

## Submission Orchestrator (Autofill + Human Gate)

Generate a portal field-map and validation report before manual submission:

```bash
python3 submission_orchestrator.py --mode dry-run
python3 submission_orchestrator.py --mode human-gate --grant-id grantsgov_361009
```

Generated artifacts:

- `output/submission_orchestrator/<grant_id>_field_map.json`
- `output/submission_orchestrator/<grant_id>_validation.json`
- `output/submission_orchestrator/<grant_id>_<mode>_review.md`

## Playwright Portal Test (Autofill)

Use Playwright to test form autofill against a portal URL. Default behavior does not submit.

Install once:

```bash
pip install playwright
playwright install chromium
```

Dry run (fills mapped fields + screenshot, no submit):

```bash
python3 submission_playwright_runner.py \
	--grant-id grantsgov_361009 \
	--portal-url "https://example-portal/form" \
	--selectors templates/portal_selectors.example.json
```

Explicit submit test (only in safe sandbox):

```bash
python3 submission_playwright_runner.py \
	--grant-id grantsgov_361009 \
	--portal-url "https://example-portal/form" \
	--selectors templates/portal_selectors.example.json \
	--confirm-submit
```

## One-Line Description

Grant is an AI funding copilot for researchers, from opportunity discovery to proposal draft generation with a mandatory human approval gate.

## Operating Guardrail

See `DEFINITION_OF_DONE.md` for the minimal success criteria and stop rules that keep Grant focused and low-friction.
