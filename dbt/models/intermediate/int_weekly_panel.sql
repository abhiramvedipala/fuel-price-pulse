-- Weekly panel: region x product x week with the crude prices that were
-- already known that Monday. A crude week ends on a Friday, so it becomes
-- usable 3 days later; the ASOF join takes the latest usable crude week
-- and never looks forward. Inner join: a retail week with no earlier crude
-- week (the very first week of a history) is dropped rather than kept null.
with retail as (
    select * from {{ ref('stg_retail_prices') }}
),

crude as (
    select
        crude_week,
        cast(crude_week + interval 3 day as date) as usable_from,
        wti,
        brent
    from {{ ref('stg_crude_prices') }}
)

select
    r.region || '|' || r.product || '|' || cast(r.week as varchar) as panel_id,
    r.region,
    r.product,
    r.week,
    r.price,
    c.crude_week,
    c.wti,
    c.brent
from retail r
asof join crude c
    on r.week >= c.usable_from
