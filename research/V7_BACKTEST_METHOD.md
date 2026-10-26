# V7 historical replay: preliminary backtesting

This preview adds an **on-demand historical replay** to each selected V6 financial-market relationship. The study re-evaluates `relationshipStability()` at historical cutoffs, passing it only rows dated no later than the checkpoint.

- Spaced checkpoints every 20 stored data rows, generally about monthly.
- Up to ~3 years of replay coverage, depending on available rows.
- The existing V6 research watch rule is unchanged: 60 paired daily changes, at least 12 qualifying reference windows, historical deviation rank >=95%, and correlation deviation >=0.35.
- Displays the number of checked dates, eligible assessments, watch flags, insufficient-data results, and last six dated flags.
- The replay is run **only when requested** on a selected edge; this does not modify the automated market updater or the live warning system.

## Scientific limitations / next research steps

1. A watch is **not** a successful prediction. These counts do not establish sensitivity, specificity, precision, or economic usefulness.
2. Histories cover unequal intervals; HY OAS history starts in 2023. The data do not include the global financial crisis and several other important stress episodes.
3. Adjacent tests and 60-observation correlation windows overlap, violating independence assumptions.
4. Historical FRED/ETF data are the currently stored revised series, not necessarily the exact values available to investors on each historical date. The replay controls lookahead from future rows but is **not yet an auditable point-in-time archive**.
5. The sampled checkpoints omit possible flags between evaluation dates; they cannot quantify alert duration.
6. Proxies based on 1-month breadth and 3-month bank drawdowns contain overlapping observations.
7. Later milestones: independently define dated stress outcomes, preserve vintage data, examine drawdowns in the 20/60 sessions after each historical signal, calculate baseline alert frequency and validate out of sample.
8. Current algorithm is descriptive exploratory research, never an investment signal.

## Review checklist
Run the Cloudflare preview build, select **Credit ↔ Volatility**, expand **Run historical replay**, and compare the counts and dates with other edges. If no eligible checks are available, the UI should say so rather than claiming no risk.
