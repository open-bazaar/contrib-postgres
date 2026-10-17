{% from "fragments.sql.tpl" import expression, predicate, returning with context %}
UPDATE {{ request.table | identifier }}
SET
{% for column, value in request.values.items() %}
    {{ column | identifier }} = {{ expression(value) }}{% if not loop.last %},{% endif %}
{% endfor %}
{% if request.where is not none %}
WHERE {{ predicate(request.where) }}
{% endif %}
{{ returning(request.returning) }}
