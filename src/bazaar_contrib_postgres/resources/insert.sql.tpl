{% from "fragments.sql.tpl" import returning %}
{% set columns = request.rows[0].keys() | list %}
INSERT INTO {{ request.table | identifier }} ({{ columns | map("identifier") | join(", ") }})
VALUES
{% for row in request.rows %}
    (
    {% for column in columns %}
        {{ bind(row[column]) }}{{ ", " if not loop.last else "" }}
    {% endfor %}
    ){{ ", " if not loop.last else "" }}
{% endfor %}
{% if request.conflict is not none %}
ON CONFLICT ({{ request.conflict.columns | map("identifier") | join(", ") }})
{% if request.conflict.update %}
DO UPDATE SET
{% for column in request.conflict.update %}
    {{ column | identifier }} = excluded.{{ column | identifier }}{% if not loop.last %},{% endif %}
{% endfor %}
{% else %}
DO NOTHING
{% endif %}
{% endif %}
{{ returning(request.returning) }}
