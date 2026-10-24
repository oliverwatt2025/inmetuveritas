# In Metu Veritas — market intelligence foundation (v1)

**Status:** architecture only. This branch adds a machine-readable catalogue and relationship graph. No production data collection, classifications, scores, frontend, or scheduled workflows are modified.

## First nightly processing design
1. Ingest each source's **latest actual observation date** and publication frequency. Prefer official feeds or rights-cleared data; missing readings remain missing and are labelled stale.
2. Generate derived metrics (rolling change, percentile, historical z-score). Maintain minimum lookback and data-quality checks. Reconcile revisions and report freshness separately from publication timestamp.
3. Score four **independent evidence families**: equity participation/volatility, corporate credit/funding, economic cycle, and monetary/liquidity conditions. Do not add a composite and its constituent as separate independent evidence.
4. Produce an evidence sheet: biggest daily/weekly/monthly changes, corroboration, disagreements, and at most three prioritised observations with precise sourced numbers.
5. Add an AI-authored summary from **only that evidence sheet**. Require each statement to reference indicator IDs and dates; reject unsupported causal or predictive language. Have rule-based fallback text if AI generation fails.
6. Publish an immutable, dated analysis JSON snapshot daily through the existing build pipeline after validation. Serve it statically on Cloudflare; no visitor-specific AI call required.

## Scope of the first iteration
The catalogue covers existing production indicators, underlying composite inputs, and carefully selected candidates. Planned data feeds are *not yet connected*. All new source names require endpoint and redistribution checks before use. This is a research plan rather than a claim about live availability.

### First implementation batch (after architecture approval)
- Derived HY spread 20-day change (from already available FRED data).
- An explicit breadth/credit/VIX disagreement rule (without double counting credit stress composite).
- Observed-at and ingested-at timestamps for every evidence item.
- A small dated **What changed / Why it matters / What would change our view** JSON report, initially rule-based.
- Unit tests for missing data, stale observations, contradictory signals, and preventing spurious certainty.

### Important analytical distinctions
- A percent-ranked signal is **not** the probability of a crash or recession.
- A daily *site update* does not mean CPI, unemployment, initial claims, or weekly Fed datasets are daily observations.
- Spread widening has different implications depending on absolute level, persistence and context.
- Observed association and causal explanation must remain distinct.
- Raw VIX, HY OAS, investment-grade OAS, credit composites and sentiment proxies contain correlated information; the model must track dependence.
- The central headline should show a qualitative risk regime, confidence in the evidence and any missing/late data; no arbitrary numeric confidence percentages.

## Future site UX
Stable relationship map, center conclusion, colored strength/recency markers, selectable nodes with five-year history, explain-why paths and a daily narrative that cites the contributing sources.

## Safety boundary
Do not change `scripts/update_indicators.py`, existing historical NDJSON, workflow schedule, or production `main` until a separate implementation PR is reviewed and tested.
