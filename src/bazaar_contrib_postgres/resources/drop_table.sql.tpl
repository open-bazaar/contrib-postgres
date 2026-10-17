DROP TABLE {% if operation.if_exists %}IF EXISTS {% endif %}{{ operation.table | identifier }}
