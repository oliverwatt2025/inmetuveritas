# V6 relationship stability — research prototype

The on-page change monitor uses existing dated observations in `public/history_5y.ndjson`, without changing data sources, AI selection, or the production risk model.

For each selected market connection, calculate Pearson correlation of **daily changes** across 60 valid paired observations. Construct a historical reference of prior 60-pair rolling estimates by stepping back 20 dataset rows at a time and leaving the most recent 60 rows out of the historical baseline. Only require consecutive dated pairs within four calendar days.

When at least 12 qualifying historical reference windows exist, calculate their median and the rank of the recent absolute distance from that median within historical absolute distances. A **provisional research watch** requires BOTH an absolute deviation of at least 0.35 and a deviation ranking in the outer 5% of this reference set.

## Limitations

- Historical windows overlap. This is a *descriptive empirical screening rule*, **not** a significance test.
- The three-year HY/IG history is insufficient for stress-era validation such as 2008 or 2020.
- Indicators may be published at different times; the stored rows approximate aligned dates, not guaranteed exchange-time synchronization.
- Breadth and KRE drawdown are rolling constructs and induce serial dependence.
- Short or constant samples are reported as insufficient rather than assigned a correlation.
- A relationship shift is not, on its own, evidence of systemic stress or a crash probability.
- Thresholds require backtesting with longer histories, alternative window sizes, and out-of-sample checks before being treated as substantive warnings.
