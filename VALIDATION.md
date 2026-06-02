# Validation — What “accuracy” means

QuickSight migration is **not** binary. This document defines checkable accuracy
for the assistant and for portfolio demos.

---

## 1. Validation layers

| Layer | Question | Automated? |
|-------|----------|------------|
| **Structural** | Do all referenced fields exist in dataset? | Yes |
| **Datasource** | Can QuickSight connect and run probe SQL? | Yes |
| **Calculation** | Do translated expressions parse in QuickSight? | Yes |
| **Metric parity** | Same numbers on fixed filter slice? | Partial |
| **Visual** | Chart type and key encodings preserved? | Manual + checklist |
| **UX** | Filters/parameters behave similarly? | Manual review |

---

## 2. Automated checks (MVP + production)

### 2.1 Datasource validation

- `DescribeDataSource` or test `CreateDataSource` in dev (then delete if ephemeral).
- Probe query: `SELECT 1` or `COUNT(*)` with row limit on primary table.
- Compare Tableau connection type vs QuickSight supported sources list.

**Pass:** all mapped sources green.  
**Fail:** deploy blocked.

### 2.2 Calculation validation

| Check | Method |
|-------|--------|
| Syntax | QuickSight `Describe` / dry-run dataset calc API or local parser rules |
| Coverage | Every Tableau calc appears in mapping or explicit `manual_required` |
| Confidence | Bedrock outputs `confidence: high|medium|low`; block deploy on `low` for KPI calcs (config) |

### 2.3 Metric parity (where feasible)

For calcs marked `high` confidence and **not** `lod` / `table_calc`:

1. Define 3–5 **golden scenarios** (parameter values + filters) in `parity_spec.yaml`.
2. Run equivalent logic:
   - Tableau: export aggregate via documented query or precomputed fixture.
   - QuickSight: run dataset query post-deploy (dev).
3. Compare within tolerance: `abs(a-b) / max(|a|,ε) < 0.01` (1% default).

**Portfolio MVP:** use **precomputed fixture CSVs** from sample data instead of live Tableau Server.

### 2.4 Visual validation

Automated:

- Count of visuals per sheet within ±N.
- Required filters present on analysis.

Manual (review UI checklist):

- Chart type acceptable substitute documented in `layout_mapping.md`.
- Color/size fidelity called out as non-blocking.

---

## 3. `migration_report.json` schema (summary)

```json
{
  "workbook_id": "demo-sales",
  "run_id": "2026-06-01T12:00:00Z",
  "overall_status": "WARN",
  "datasource_checks": [{ "name": "Sales", "status": "PASS" }],
  "calc_checks": {
    "total": 12,
    "high_confidence": 8,
    "manual_required": 2,
    "failed_syntax": 0
  },
  "parity_checks": [{ "scenario": "NA_YTD", "status": "PASS", "delta_pct": 0.002 }],
  "visual_checks": { "status": "MANUAL_REVIEW", "gaps": ["dual_axis → combo approx"] },
  "deploy_allowed": false,
  "blockers": ["2 calcs require manual rewrite"]
}
```

`deploy_allowed` true only when no `FAIL` blockers and approval recorded.

---

## 4. What we tell stakeholders

- **Guarantee:** validated connections + parseable calcs + documented gaps.
- **Do not guarantee:** pixel-perfect dashboards or full LOD parity without engineer time.
- **Q topics:** semantic accuracy tied to **published** workbook documentation, not raw AI guess.

---

*Validation v1.0*
