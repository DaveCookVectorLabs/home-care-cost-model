# Home Care Cost Model — Observable Notebook

Companion notebook to the working paper *The Home Care Cost Model: Personal
Support, Housekeeping, and Service Mix Decisions for Aging in Place in
Canada* (Cook, 2026).

This notebook loads the published datasets and explores three headline
findings: hybrid savings versus all-PSW plans, tax relief effectiveness
across the income distribution, and the cross-province subsidy gap.

All data is deterministic and under CC BY 4.0. Code is MIT-licensed. This
is a reference framework, not clinical or financial advice.

```js
scenarios = FileAttachment("home_care_scenarios.csv").csv({typed: true})
```

```js
archetypes = FileAttachment("home_care_cost_model_archetypes.csv").csv({typed: true})
```

```js
subsidy_gap = FileAttachment("home_care_subsidy_gap.csv").csv({typed: true})
```

## Finding 1 — Hybrid savings distribution

Distribution of hybrid savings as a fraction of the all-PSW counterfactual,
across the 5,000 synthetic scenarios where housekeeping hours are positive.

```js
Plot.plot({
  title: "Hybrid savings as % of all-PSW counterfactual",
  marks: [
    Plot.rectY(
      scenarios.filter(d => d.recommended_housekeeping_hours_per_week > 0),
      Plot.binX({y: "count"}, {
        x: d => (d.hybrid_savings_vs_all_psw_monthly_cad /
                 d.all_psw_cost_comparison_monthly_cad) * 100,
        fill: "#E87A2D"
      })
    )
  ],
  x: {label: "savings %"},
  y: {label: "scenarios"}
})
```

## Finding 2 — Subsidy gap by province

```js
Plot.plot({
  title: "Monthly dollar gap between subsidised and recommended hours, by province",
  marginLeft: 60,
  marks: [
    Plot.barX(
      d3.rollup(subsidy_gap, v => d3.mean(v, d => d.dollar_gap_monthly_cad), d => d.jurisdiction_code),
      {x: d => d[1], y: d => d[0], fill: "#7A7168"}
    )
  ],
  x: {label: "CAD per month"},
  y: {label: "jurisdiction"}
})
```

## Disclaimer

Reference model only. Not clinical or financial advice; consult a regulated
health professional or registered tax practitioner for individual decisions.
