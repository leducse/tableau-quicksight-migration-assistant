# Layout Mapping — Regional Sales Performance

Approximate Tableau → QuickSight visual mapping. Gaps are surfaced (not hidden) for human review. Pixel-perfect parity is **not** a goal of v1.

## Worksheet visual mapping

| Worksheet | Tableau chart | QuickSight visual | Confidence | Gap |
|-----------|---------------|-------------------|------------|-----|
| Sales by Region | bar | BarChartVisual | high | — |
| Profit Trend | line | LineChartVisual | high | — |
| Sales vs Profit | scatter | ScatterPlotVisual | high | — |
| Category Heatmap | dual_axis | ComboChartVisual | medium | dual_axis → combo approx |
| Segment Mix | pie | PieChartVisual | high | — |

## Documented gaps

- **Category Heatmap**: dual_axis → combo approx (non-blocking, review color/encoding fidelity).

## Dashboards

### Executive Overview
- Visuals: Sales by Region, Profit Trend, Segment Mix
- Filters as QuickSight controls: Region, Order Year
- Parameters as QuickSight parameters: Target Margin

### Category Detail
- Visuals: Sales vs Profit, Category Heatmap
- Filters as QuickSight controls: Segment
- Parameters as QuickSight parameters: none

## Not auto-migrated (manual follow-up)

- Tableau LOD expressions (FIXED/INCLUDE/EXCLUDE) → rebuild with QuickSight level-aware calcs.
- Table calculations (RUNNING_*, WINDOW_*, INDEX, RANK) → rebuild on the QuickSight visual.
- ATTR() aggregation → confirm intended aggregation in QuickSight.
- Custom color palettes, tooltips, and exact sizing → manual styling.
