# Prompt: Calculation Translation (calc-v1)

Versioned template used by the **guarded** Bedrock provider. The local MVP uses
the rule-based translator in `src/generator/mock.py`; this file documents the
production multi-step flow (propose -> self-critique -> emit) referenced by
REQUIREMENTS M24-M26.

## Inputs (structured, metadata only)

- `tableau_name`, `tableau_formula`, `datatype`, `role`
- Available dataset fields (names + QuickSight column types)

## Step 1 — Propose

> Translate the following Tableau calculated field into a QuickSight calculated
> field expression. Use QuickSight function names (sum, avg, ifelse, dateDiff,
> extract, toUpper, ...). Reference fields as `{Field Name}`. Return JSON:
> `{ "quicksight_expression": str, "confidence": "high|medium|low", "category": str, "manual_required": bool, "notes": [str] }`.

## Step 2 — Self-critique

> Given the metadata.json field list, verify every referenced field exists and
> the expression parses. Flag LOD (FIXED/INCLUDE/EXCLUDE), table calcs, and ATTR
> as `manual_required: true` with `confidence: low`. Return the revised JSON.

## Step 3 — Summarize

> Summarize unmapped/low-confidence calcs into `layout_mapping.md` notes.

## Audit

Each run records `prompt_version=calc-v1` and the Bedrock `model_id` in the
calculation notes and `manifest.yaml`.
