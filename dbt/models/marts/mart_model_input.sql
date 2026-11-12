-- Model mart: the clean panel the forecaster reads. Features are built in
-- Python (fuelpulse/features.py) so one code path serves training,
-- backtesting and the leakage test.
select
    panel_id,
    region,
    product,
    week,
    price,
    wti,
    brent
from {{ ref('int_weekly_panel') }}
