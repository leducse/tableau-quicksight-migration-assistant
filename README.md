# Tableau → QuickSight Migration Assistant

**Status:** Spec only — not yet implemented.

Accelerates **Tableau to Amazon QuickSight** migrations by reusing condensed
workbook metadata, using generative AI to propose datasets/calculations/visuals,
emitting **reviewable AWS deployment artifacts** (SDK scripts / IaC), and
producing **validation reports** plus **Amazon Q in QuickSight** topic assets.

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
