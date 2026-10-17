{% from "fragments.sql.tpl" import expression, predicate with context %}
SELECT {% if request.distinct %}DISTINCT {% endif %}
{% for alias, value in request.columns.items() %}
    {{ expression(value) }} AS {{ alias | identifier }}{% if not loop.last %},{% endif %}
{% else %}
    *
{% endfor %}
FROM {{ request.table | identifier }}{% if request.alias %} AS {{ request.alias | identifier }}{% endif %}

{% for join in request.joins %}
{{ join.kind | upper }} JOIN {{ join.table | identifier }}{% if join.alias %} AS {{ join.alias | identifier }}{% endif %}

    ON {{ predicate(join.on) }}
{% endfor %}
{% if request.where is not none %}
WHERE {{ predicate(request.where) }}
{% endif %}
{% if request.group_by %}
GROUP BY {% for value in request.group_by %}{{ expression(value) }}{% if not loop.last %}, {% endif %}{% endfor %}

{% endif %}
{% if request.having is not none %}
HAVING {{ predicate(request.having) }}
{% endif %}
{% if request.order_by %}
ORDER BY
{% for item in request.order_by %}
    {{ expression(item.expression) }} {{ "DESC" if item.descending else "ASC" }} NULLS {{ item.nulls | upper }}{% if not loop.last %},{% endif %}
{% endfor %}
{% endif %}
{% if request.limit is not none or request.offset %}
LIMIT {{ bind(request.limit) }}
{% endif %}
{% if request.offset %}
OFFSET {{ bind(request.offset) }}
{% endif %}
