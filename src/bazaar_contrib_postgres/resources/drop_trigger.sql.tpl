DROP TRIGGER {% if operation.if_exists %}IF EXISTS {% endif %}{{ operation.name | identifier }} ON {{ operation.table | identifier }}
