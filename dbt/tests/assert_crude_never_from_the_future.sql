-- The crude week joined to a retail week must have ended before it,
-- and not be stale by more than three weeks (holiday reporting gaps).
select *
from {{ ref('int_weekly_panel') }}
where crude_week >= week
   or crude_week < week - interval 24 day
