# V8 exploratory forward-outcome validation

This V8 *research preview* begins separating a relationship-change warning from a subsequent, independently specified market outcome.

**Signal rule:** the existing V6 research-watch rule, evaluated at historical checkpoints (roughly 20 stored rows apart) using prior data only.

**Outcome definition, chosen in advance:** in the next 20 dated observations, the 1-month SPY drawdown proxy reaches **−8% or lower**. Exclude checkpoints already at or below −8%, because these are not prospective stress onsets. At least 16 of the 20 outcome observations must be present to classify no event or an event. Missing outcomes remain unknown.

The panel reports eligible research signals, qualifying watch signals, drawdown outcomes following watch signals, drawdown outcomes following ordinary signals, and unresolved outcomes. **With zero watches, precision is undefined**, not zero or perfect.

## What this does NOT prove

- Not an out-of-sample test, and threshold tuning against these observations risks overfitting.
- Data are reconstructed and sometimes revised, **not vintage-accurate point-in-time values**.
- SPY 1-month drawdown is a rolling proxy and can overlap with the equity-breadth signal.
- Watch observations and outcomes can share windows or market regimes. Checkpoints are not statistically independent.
- The backtest has no 2008/2020 HY/IG credit history, so it cannot measure performance through major stress episodes.
- No statistical significance, causal inference, live alert, crash prediction, or calibrated accuracy claim is made.
- If there are no watch cases, the tool cannot estimate successful watch outcomes.

## Next prerequisites

Obtain 15–20 years of properly dated underlying prices and credit spreads, retain source/vintage metadata, define multiple outcomes before research, use blocked time-based out-of-sample testing, and publish denominators and uncertainty intervals before discussing forecasting value.
