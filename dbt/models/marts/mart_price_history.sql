-- Dashboard mart: price history with the changes a station owner reads.
select
    panel_id,
    region,
    product,
    week,
    price,
    wti,
    brent,
    price - lag(price) over w as change_1w,
    price - lag(price, 52) over w as change_52w,
    avg(price) over (w rows between 3 preceding and current row) as avg_4w,
    -- retail price minus crude cost per gallon (42 gallons per barrel)
    price - wti / 42.0 as spread_over_wti
from {{ ref('int_weekly_panel') }}
window w as (partition by region, product order by week)
