-- Every region x product series must be contiguous: exactly 7 days
-- between consecutive weeks. Lag features assume this.
select *
from (
    select
        region,
        product,
        week,
        lag(week) over (partition by region, product order by week) as prev_week
    from {{ ref('int_weekly_panel') }}
)
where prev_week is not null and week - prev_week <> 7
