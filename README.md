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

## Product Positioning

Grant is an AI funding copilot, not an autonomous submitter.
Final decisions and submission actions remain under human control.

## Core Workflow

`discover -> rank -> draft -> submission-ready package`

## Discovery Sources

- `mock`
- `vinnova_api`
- `grants_gov_api`
- `eu_sedia_api`

## Run

```bash
python3 run_pipeline.py --top-k 3
python3 run_pipeline.py --discovery-source eu_sedia_api --eu-sedia-text "artificial intelligence"
```

Use custom eligibility rules:

```bash
python3 run_pipeline.py --eligibility-rules eligibility_rules.yaml
```

## One-Line Description

Grant is an AI funding copilot for researchers, from opportunity discovery to proposal draft generation with a mandatory human approval gate.
