{% from "fragments.sql.tpl" import column_definition with context %}
ALTER TABLE {{ operation.table | identifier }}
ADD COLUMN {{ column_definition(operation.column) }}
