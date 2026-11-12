-- One row per region x product x week, retail price in USD per gallon.
select
    s.region,
    s.product,
    r.week,
    r.value as price
from {{ source('eia', 'raw_prices') }} r
join {{ ref('series') }} s using (series_id)
where s.unit = 'usd_per_gal'
