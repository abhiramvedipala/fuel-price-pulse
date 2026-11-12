## What this builds
- `python -m fuelpulse.explain`: exact SHAP for the four horizon models, per-region and fuel driver ranking, and the six worst 4-week backtest misses.
- `docs/findings.md`: one-page plain-English report for a gas-station owner.

## How it was tested
- `scripts/check.sh` passes. The numbers in the findings page were each checked against `reports/backtest.md` and `reports/shap.md`; one unbacked claim was removed and the momentum claim was verified (correlation +0.41).

## Numbers (`uv run python -m fuelpulse.explain`)
- Top drivers (mean absolute SHAP, $/gal): last week's change 0.0322, WTI level 0.0163, seasonal term 0.0148.
- Same top three in all 12 series. Holiday-week flag contributes about zero.
- Worst 4-week misses: March 2026 (errors $0.79 to $1.25/gal, forecast too low).

## Open questions
- None.
