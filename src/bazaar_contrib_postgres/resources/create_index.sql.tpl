{% from "fragments.sql.tpl" import predicate, expression with context %}
CREATE {% if operation.index.unique %}UNIQUE {% endif %}INDEX {% if operation.if_not_exists %}IF NOT EXISTS {% endif %}{{ operation.index.name | identifier }}
ON {{ operation.table | identifier }} (
{% for column in operation.index.columns %}
    {{ column | identifier }}{{ ", " if not loop.last or operation.index.order_by else "" }}
{% endfor %}
{% for sort in operation.index.order_by %}
    {{ expression(sort.expression) }} {{ "DESC" if sort.descending else "ASC" }}{{ ", " if not loop.last else "" }}
{% endfor %}
)
{% if operation.index.where is not none %}
WHERE {{ predicate(operation.index.where) }}
{% endif %}
