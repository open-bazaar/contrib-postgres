{% from "fragments.sql.tpl" import predicate, returning with context %}
DELETE FROM {{ request.table | identifier }}
{% if request.where is not none %}
WHERE {{ predicate(request.where) }}
{% endif %}
{{ returning(request.returning) }}
