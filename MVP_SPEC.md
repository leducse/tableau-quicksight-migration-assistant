# MVP Spec — Portfolio Demo

> Prove the **migration assistant loop** on one sanitized workbook without
> requiring production Tableau Server or a large QuickSight estate.

---

## MVP outcome (demo story)

1. Load `samples/demo_metadata.json` (same shape as Workbook Knowledge Platform).
2. Bedrock generates `calculations.yaml`, `visuals.yaml`, `q_topics.yaml`.
3. Rule-based validator produces `migration_report.json` (1 WARN, 0 blockers after fix).
4. `deploy.py --dry-run` prints QuickSight API plan.
5. Optional: `--deploy-dev` creates one dataset + one analysis in your dev account.
6. Review checklist UI or markdown report for human sign-off.

---

## In / out

| In | Out |
|----|-----|
| Sample metadata + fixture parity CSVs | Live Tableau REST |
| Bedrock calc + visual mapping | Full Step Functions workflow |
| boto3 dry-run plan | Asset bundle cross-account promotion |
| Q topic YAML generation | Auto prod deploy |
| `migration_report.json` | Pixel-perfect layout |
| Shared parser copy or git submodule pointer | Full web review UI (CLI ok) |

---

## Repo layout (when built)

```text
tableau-quicksight-migration-assistant/
├── samples/
│   ├── demo_metadata.json
│   └── parity_fixtures/
├── src/
│   ├── mapper/           # datasource, calc, visual
│   ├── generator/        # Bedrock prompts
│   ├── package/          # assemble S3 layout
│   ├── validator/
│   └── deploy/           # deploy.py
├── prompts/              # versioned prompt templates
├── infra/cdk/            # S3, Lambda, optional QS dev role
└── scripts/
    └── run_migration.py  # local end-to-end
```

**Optional:** `lib/tableau_metadata/` copied from workbook platform parser later.

---

## AWS stack (minimal)

| Service | Use |
|---------|-----|
| S3 | Store migration packages |
| Lambda | `run_migration` orchestrator (single function ok) |
| Bedrock | Claude for yaml/markdown generation |
| IAM role | QuickSight dev account (deploy only) |
| Secrets Manager | Warehouse read-only creds for parity queries |

No DynamoDB in MVP—status in `manifest.json` on S3.

---

## Bedrock flow (single Lambda, 3 calls)

1. **Propose** mappings → draft yaml fragments.  
2. **Critique** draft against `metadata.json` → revised yaml.  
3. **Summarize** gaps → `layout_mapping.md` + validation hints.

---

## `deploy.py` (MVP behavior)

```bash
python deploy.py --package s3://bucket/migrations/demo-sales/run1 --dry-run
python deploy.py --package ... --deploy-dev --profile dev
```

Dry-run outputs ordered API actions:

- `CreateDataSource` (or reuse)
- `CreateDataSet`
- `CreateAnalysis`
- `CreateDashboard` (if in scope)

Use idempotent names: `migration-demo-sales-{resource}`.

---

## Q topics (MVP)

Generate `q_topics.yaml` from:

- `demo_metadata.json` column/field names
- Optional `samples/demo_published_doc.md` (stub glossary)

Do not call QuickSight Q APIs in MVP unless trivial; **artifact generation is enough** for portfolio.

---

## Implementation order

| Step | Days (est.) |
|------|-------------|
| 1 Sample metadata + parity fixtures | 1 |
| 2 Calc/visual mapping prompts + parser for yaml | 2–3 |
| 3 Validator + migration_report | 1–2 |
| 4 deploy.py dry-run | 1 |
| 5 Optional dev deploy + README demo | 1–2 |

**Total:** ~1–2 weeks part-time.

---

## Success criteria

- [ ] End-to-end `run_migration.py` on sample without AWS (except Bedrock)
- [ ] `migration_report.json` with clear PASS/WARN/FAIL
- [ ] Dry-run plan readable by a BI engineer
- [ ] README links to workbook knowledge platform
- [ ] Documented list of Tableau features **not** auto-migrated

---

## Link to workbook platform

For portfolio narrative:

1. **Document** workbook (Knowledge Platform).  
2. **Migrate** workbook (this repo).  
3. **Govern queries** on new QS data (MCP query governance repo).

---

*MVP v1.0*
