# Grant

<p align="center">
	<img src="assets/grant-logo.png" alt="Grant logo" width="220" />
</p>

Grant is an AI agent that helps researchers find and apply for research funding.

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

## One-Line Description

Grant is an AI funding copilot for researchers, from opportunity discovery to proposal draft generation with a mandatory human approval gate.

## Operating Guardrail

See `DEFINITION_OF_DONE.md` for the minimal success criteria and stop rules that keep Grant focused and low-friction.
