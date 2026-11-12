-- Weekly WTI and Brent spot, USD per barrel. EIA dates crude weeks by
-- their Friday end date, retail weeks by Monday.
select
    r.week as crude_week,
    max(case when s.product = 'wti' then r.value end) as wti,
    max(case when s.product = 'brent' then r.value end) as brent
from {{ source('eia', 'raw_prices') }} r
join {{ ref('series') }} s using (series_id)
where s.unit = 'usd_per_bbl'
group by 1
