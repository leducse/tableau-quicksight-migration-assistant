# Tableau → QuickSight Migration Assistant

**Status:** MVP built — runs end-to-end locally with no AWS credentials.

Accelerates **Tableau to Amazon QuickSight** migrations by reusing condensed
workbook metadata, using generative AI to propose datasets/calculations/visuals,
emitting **reviewable AWS deployment artifacts** (SDK scripts / IaC), and
producing **validation reports** plus **Amazon Q in QuickSight** topic assets.

> **Local demo note:** GenAI generation and QuickSight deployment are
> **mocked / dry-run** locally. Calculation, visual, and Q-topic generation run
> behind a swappable interface whose default implementation is a deterministic
> **rule-based** translator (no Bedrock call). `deploy.py` defaults to
> **`--dry-run`** and never calls QuickSight. A clearly-marked, guarded Bedrock
> + `--deploy-dev` path exists but is off by default and requires AWS creds.

## Run the MVP

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 1. End-to-end local loop (map -> generate -> package -> validate)
python scripts/run_migration.py

# 2. Print the ordered QuickSight API plan (no AWS mutations)
python deploy/deploy.py --package . --dry-run
```

Outputs (committed as demo artifacts):

| Artifact | Purpose |
|----------|---------|
| `mappings/datasources.yaml` / `datasets.yaml` | Tableau connections → QuickSight data sources/datasets |
| `mappings/calculations.yaml` | Tableau calc → QuickSight expression + confidence + notes |
| `mappings/visuals.yaml` | Worksheet/dashboard → QuickSight visual types |
| `generated/layout_mapping.md` | Documented visual gaps (not hidden) |
| `generated/q_topics.yaml` | Amazon Q topic definition |
| `validation/migration_report.json` | PASS/WARN/FAIL + `deploy_allowed` |
| `deploy/dry_run_plan.json` | Ordered Create* API plan |

## Architecture (code)

```text
src/
  mapper/      datasource.py, calc.py, visual.py
  generator/   base.py (interface), mock.py (rule-based), bedrock.py (guarded), factory.py
  package/     builder.py (assembles package + manifest)
  validator/   engine.py (structural/datasource/calc/parity/visual checks)
  deploy/      planner.py (ordered QuickSight API plan)
deploy/deploy.py     CLI (--dry-run default, --deploy-dev guarded)
scripts/run_migration.py   local end-to-end loop
samples/     demo_metadata.json + parity_fixtures/
prompts/     versioned Bedrock prompt templates (documentation)
```

## Validation checks implemented (see `VALIDATION.md`)

- **Structural** — every referenced field exists in a mapped dataset.
- **Datasource** — Tableau connection class is an auto-mappable QuickSight source.
- **Calculation** — syntax (balanced/non-empty), coverage, and confidence gating
  (KPI calcs must be high confidence or deploy is blocked).
- **Metric parity** — precomputed fixture CSVs compared within 1% tolerance for
  high-confidence, non-LOD/non-table-calc metrics.
- **Visual** — visual count per dashboard, required filters present, documented gaps.

`migration_report.json` reports `deploy_allowed = (no FAIL blockers) AND approval recorded`.

## Tableau features NOT auto-migrated (manual follow-up)

- LOD expressions (`FIXED`/`INCLUDE`/`EXCLUDE`)
- Table calculations (`RUNNING_*`, `WINDOW_*`, `INDEX`, `RANK`, `LOOKUP`)
- `ATTR()` aggregation
- Custom color palettes, tooltips, exact sizing (pixel-perfect parity is a non-goal)

## Sibling project

Shares the Tableau ingest layer with
[`tableau-workbook-knowledge-platform`](../tableau-workbook-knowledge-platform/)
(formerly Project Prism). That repo owns **documentation**; this repo owns
**migration generation and validation**.

```text
tableau-workbook-knowledge-platform  →  metadata.json + field-trusted docs
tableau-quicksight-migration-assistant →  QuickSight assets + Q topics + deploy
```

## Documents

| File | Purpose |
|------|---------|
| [`REQUIREMENTS.md`](REQUIREMENTS.md) | Goals, pipeline, validation, Q topics, non-goals |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Components, artifact model, human-in-the-loop gates |
| [`MVP_SPEC.md`](MVP_SPEC.md) | Portfolio MVP on AWS (sample workbook, dry-run deploy) |
| [`VALIDATION.md`](VALIDATION.md) | How “accuracy” is defined and tested |

## Disclaimer

Portfolio work uses **sanitized sample workbooks** and a **dev QuickSight**
account. Generated assets require human review before production promotion.
