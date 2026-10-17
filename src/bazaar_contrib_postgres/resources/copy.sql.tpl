INSERT INTO {{ request.table | identifier }} ({{ request.query.columns | map("identifier") | join(", ") }})
{% set request = request.query %}
{% include "select.sql.tpl" %}
