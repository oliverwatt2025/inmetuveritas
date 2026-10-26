# V9 — Long-run credit-spread research archive

This adds a **separate** FRED archive for US high-yield and investment-grade option-adjusted spreads covering approximately 20 calendar years. Its purpose is to include the 2008 global financial crisis, the COVID-19 shock, and other cycles in subsequent calibration.

Source FRED series:
- `BAMLH0A0HYM2` — ICE BofA US High Yield Index Option-Adjusted Spread.
- `BAMLC0A0CM` — ICE BofA US Corporate Index Option-Adjusted Spread.

FRED spreads are expressed in **percent**; stored values are converted to **basis points** (multiplied by 100). Observations retain exact provider dates and do not carry forward weekend/holiday data.

The new independent workflow `.github/workflows/credit-history-20y.yml` supports manual execution on the development branch and weekly refresh on the default branch after release. It requires the existing `FRED_API_KEY` repository secret.

The workflow **rejects** publication if either series has fewer than 3,500 dated points, lacks observations from 2008 or lacks recent observations, avoiding the accidental publication of truncated histories. A FRED API outage preserves the existing archive; if neither series updates, it exits without rewriting it.

The archive is `public/credit_history_20y.ndjson`. It **does not replace** `history_5y.ndjson`, the nine gauges, daily AI evidence or production snapshots.

## Validation requirements before using the archive for risk classifications

1. Execute the archive workflow on `v9-long-credit-history` and inspect dated counts/first and last dates. It will commit a new archive file on the branch.
2. Confirm actual 2008 and 2020 spreads, source definition, basis-point units, observations and usage/attribution requirements.
3. Treat the archive as **historical reference data**; data vintages may have revisions and differences from what was contemporaneously available.
4. Independently define stress episodes and outcome windows. Backtest thresholds with blocked time-series splits before allowing the archive to change production risk classifications.
5. Because this FRED history is dependent on third-party index datasets, verify licensing and permitted public redistribution before merging the generated raw archive into a publicly served website. If redistribution is not permitted, publish only derived research statistics consistent with the source terms instead.

Current stage: data acquisition infrastructure only. No new 20-year percentile claims yet.
