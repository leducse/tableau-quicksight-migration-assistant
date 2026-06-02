# Requirements — Tableau → QuickSight Migration Assistant

---

## 1. Problem

- Organization is **migrating from Tableau to Amazon QuickSight** (and Quick Suite / Q).
- Manual rebuild of dashboards is slow: calcs, datasources, layout, and Q assets differ.
- Tableau workbooks encode logic the field already trusts—but QuickSight uses
  different expression syntax, asset model, and deployment APIs.
- Teams need **repeatable, validated migration packages**, not one-off consultant scripts.

## 2. Goals

| Goal | Measure |
|------|---------|
| Reduce time to first QuickSight draft | Days → hours per dashboard (with review) |
| Validated datasources | Connection tests pass before deploy |
| Validated calculations | Parity checks on sample queries / golden metrics |
| Similar look and feel | Layout mapping doc + visual type choices reviewed |
| Q readiness | Q topics + supporting documentation generated |
| Safe deployment | Human approval; dev → prod promotion path |

## 3. Users

| Persona | Need |
|---------|------|
| BI engineer | Review generated assets, run deploy, fix gaps |
| Data platform | Approve datasource mappings and RLS |
| Migration lead | Status per workbook, validation scores |
| Field stakeholder | Sign-off on metric parity (not pixel-perfect clones) |

## 4. Pipeline (target state)

```text
Input: workbook_id (or Tableau REST download)
    → shared metadata.json (from Workbook Knowledge Platform or local parser)
    → map datasources → QuickSight datasets (validated connections)
    → translate calculated fields (Bedrock + rule assist)
    → map worksheets/dashboards → QuickSight analyses/dashboards (Bedrock + templates)
    → generate Q topics + Q documentation (Bedrock)
    → emit deployment package (boto3 script and/or CDK/CloudFormation)
    → run validation suite → migration_report.json
    → human review UI → approve → deploy to QuickSight (dev)
    → optional: promote bundle to prod via CI
```

## 5. Functional requirements

### 5.1 Ingest (shared)

| ID | Requirement |
|----|-------------|
| M1 | Accept `metadata.json` produced by workbook knowledge platform (or run embedded parser). |
| M2 | Version and hash Tableau source; store beside migration artifacts in S3. |
| M3 | Support workbook scope: single dashboard migration unit per run (v1). |

### 5.2 Datasource & dataset mapping

| ID | Requirement |
|----|-------------|
| M4 | Propose QuickSight **data source** config (Redshift, Athena, RDS, etc.) from Tableau connection metadata. |
| M5 | **Validate** connectivity (test query / `DescribeDataSource`) before including in deploy package. |
| M6 | Map tables/custom SQL to QuickSight **datasets** with column types and rename rules. |
| M7 | Flag unsupported connections (extract-only, unsupported drivers) for manual follow-up. |

### 5.3 Calculations

| ID | Requirement |
|----|-------------|
| M8 | Translate Tableau calculated fields to QuickSight expressions with confidence score. |
| M9 | Maintain mapping table: `tableau_calc_id` → `quicksight_calc_name` + notes. |
| M10 | Flag constructs needing manual rewrite (LOD, table calcs, ATTR, etc.). |
| M11 | Run **parity validation** where possible (see [`VALIDATION.md`](VALIDATION.md)). |

### 5.4 Visuals & layout

| ID | Requirement |
|----|-------------|
| M12 | Map Tableau chart types to nearest QuickSight visual types (with limitations doc). |
| M13 | Preserve filters, parameters (as QuickSight controls), and sheet layout **approximately**. |
| M14 | Generate `layout_mapping.md` explaining visual gaps (not hidden). |
| M15 | Do not claim pixel-perfect parity in v1. |

### 5.5 Deployment artifacts

| ID | Requirement |
|----|-------------|
| M16 | Output **machine-readable package** under S3: `migration/{workbook_id}/{version}/`. |
| M17 | Include **boto3 deploy script** or **CDK construct** that creates/updates datasets, analyses, dashboards. |
| M18 | Support **dry-run** mode (plan only, no AWS mutations). |
| M19 | Idempotent deploy where QuickSight APIs allow (update vs create). |
| M20 | Optional: [QuickSight asset bundle](https://docs.aws.amazon.com/quicksight/latest/developerguide/asset-bundle.html) import/export for promotion between accounts. |

### 5.6 Amazon Q (Quick Suite)

| ID | Requirement |
|----|-------------|
| M21 | Generate **Q topic** definitions from published workbook documentation + metrics glossary. |
| M22 | Generate **Q-friendly documentation** (synonyms, approved questions, column descriptions). |
| M23 | Link Q topics to migrated datasets/columns where possible. |

### 5.7 GenAI (Bedrock)

| ID | Requirement |
|----|-------------|
| M24 | Use structured prompts with **metadata.json only** (not raw TWB in prompt). |
| M25 | Multi-step: propose → self-critique → emit final JSON/YAML artifacts. |
| M26 | Store prompt version and model id per migration run for audit. |

### 5.8 Human review

| ID | Requirement |
|----|-------------|
| M27 | Web UI or CLI review: validation report, calc mapping, layout notes. |
| M28 | States: `generated` → `in_review` → `approved` → `deployed_dev` → `deployed_prod`. |
| M29 | Block deploy if critical validation checks fail (configurable). |

## 6. Non-goals (v1)

- Unattended production deploy without human approval.
- 100% automatic LOD / advanced table calc translation.
- Migrating Tableau Server permissions model 1:1 (separate IAM/QS namespace work).
- Replacing the documentation platform (sibling repo).
- Migrating non-QuickSight BI targets.

## 7. AWS services

| Service | Role |
|---------|------|
| S3 | Migration packages, reports, metadata |
| Lambda | Orchestration steps, validation hooks |
| Step Functions | Multi-step migration workflow (optional) |
| Amazon Bedrock | Calc/visual/Q generation |
| QuickSight APIs | Create/update assets, bundle import |
| DynamoDB | Migration job registry and status |
| API Gateway + Cognito | Review UI API (optional MVP: CLI only) |
| Secrets Manager | QuickSight / warehouse credentials for validation |
| CloudWatch | Logs and audit |

## 8. Success metrics

| Metric | Target (program level) |
|--------|------------------------|
| Workbooks with generated dev draft | Migration backlog coverage |
| Calc parity (automated checks) | ≥80% of **simple** calcs pass; complex flagged |
| Datasource validation pass rate | 100% before deploy allowed |
| Time to dev dashboard | &lt;1 day reviewed draft per medium workbook |
| Production incidents from migration | Trend down vs manual rebuild |

---

*Requirements v1.0*
