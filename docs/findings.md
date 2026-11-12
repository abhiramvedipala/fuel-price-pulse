# What moves fuel prices, and how far ahead you can trust a forecast

*For a gas-station owner. Based on 12 years of weekly U.S. government (EIA) price data, 2015 to November 2026. Every number comes from `reports/backtest.md` and `reports/shap.md`, produced by `uv run python -m fuelpulse.backtest` and `uv run python -m fuelpulse.explain`.*

## What moves prices

1. **Last week's move is the strongest signal.** Pump prices carry momentum: a week that rose tends to be followed by more of the same, and a drop tends to keep going. This was the top driver in all 12 region and fuel combinations.
2. **Crude oil comes second.** The level of WTI crude and its recent change both matter. One barrel holds 42 gallons, so a $1 move in crude is worth roughly 2.4 cents a gallon at the pump, with a delay. In March 2026 crude went from about $65 to $96 in four weeks, and regular gasoline went from $2.94 to $3.96.
3. **Time of year is third.** The model finds a clear seasonal pattern in the weeks ahead (the spring and summer rise, the autumn fall).
4. **Your margin over crude matters less than those three.** The gap between the pump price and crude cost tends to snap back toward normal, but it is a smaller effect.
5. **Holiday weeks showed no strong effect.** Memorial Day, July 4th, Labor Day and Thanksgiving weeks did not rank among the main drivers.

The ranking is the same in every region (U.S., East Coast, Midwest, Gulf Coast, Rocky Mountain, West Coast), for both gasoline and diesel.

## How far ahead you can trust the forecast

I tested it the way you would use it: each week, forecast using only what was known then, and score it against what happened. That was repeated for 104 weeks (October 2024 to October 2026).

| Weeks ahead | Typical miss | Usual range around the forecast | Verdict |
|---|---|---|---|
| 1 | about 7 cents | plus or minus 7.5 cents | Trust it |
| 2 | about 13 cents | plus or minus 13 cents | Good for planning |
| 3 | about 18 cents | plus or minus 18 cents | Treat as a rough guide |
| 4 | about 22 cents | plus or minus 22 cents | Barely better than "no change" |

- The model beat a simple "same as last week" guess at 1 week (6% smaller misses) and was about even at 2 weeks. At 3 and 4 weeks it was **worse** than assuming prices stay where they are (2% and 5% bigger misses). So past two weeks, "no change" is a fair forecast, and the model's range is what adds value.
- It was clearly better than a "same as last year" guess at every horizon.
- The ranges are **too narrow**. They were meant to hold 8 times in 10 but held about 7 times in 10 (68.5%). Treat them as a floor on how wrong the forecast can be.

## Where it failed

The worst weeks were all supply shocks that crude oil had not yet shown:

| Target week | Average miss | What happened |
|---|---|---|
| 23 and 30 March, 16 and 9 March 2026 | $0.79 to $1.25 too low | Prices jumped about $0.87 to $1.33 in four weeks. The model, built on past calm and moderate moves, forecast almost none of it. |
| 3 August 2026 | $0.71 too low | A second sharp rise. |
| 22 June 2026 | $0.71 too high | The model expected the rise to continue, and prices fell $0.63. |

A weekly model cannot see a pipeline outage, a refinery fire or a policy change coming. When one of those hits, ignore the forecast and look at crude and wholesale prices directly.

## What to watch

- **WTI crude, week over week.** A jump of $5 or more in a week is a warning that pump prices will follow within one to three weeks.
- **Last week's pump change.** If it was large, expect more in the same direction next week.
- **The forecast range, not just the middle.** If your buying or pricing decision would be wrong at the edge of the range, wait for the next week's data.
- **The weekly refresh.** The dashboard updates every Monday after EIA publishes.

## Limits

- Prices are weekly regional averages, not your local market. Use them for direction and timing, not for a specific street price.
- The data only covers 2015 onward and one large shock in the test period (March 2026). Behaviour in a different kind of shock is untested.
- This is not financial advice.
