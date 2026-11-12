{% test max_age_days(model, column_name, days) %}
-- Fails when the newest date in the column is older than `days` days.
select max({{ column_name }}) as newest
from {{ model }}
having max({{ column_name }}) < current_date - {{ days }}
{% endtest %}
