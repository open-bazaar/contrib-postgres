{% from "fragments.sql.tpl" import predicate with context %}
CREATE TRIGGER {{ operation.name | identifier }} AFTER {{ operation.event | upper }} ON {{ operation.table | identifier }}
FOR EACH ROW {% if operation.when is not none %}WHEN ({{ predicate(operation.when) }}){% endif %}
EXECUTE FUNCTION {{ operation.name | identifier }}()
