CREATE INDEX {% if operation.if_not_exists %}IF NOT EXISTS {% endif %}{{ operation.index.name | identifier }}
ON {{ operation.table | identifier }} USING GIN (
{% for column in operation.index.columns %}
    {{ column | identifier }} gin_trgm_ops{% if not loop.last %},{% endif %}
{% endfor %}
)
