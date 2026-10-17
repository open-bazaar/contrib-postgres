{% from "fragments.sql.tpl" import column_definition, predicate with context %}
{% set table = operation.table %}
CREATE {% if operation.temporary %}TEMPORARY {% endif %}TABLE {% if operation.if_not_exists %}IF NOT EXISTS {% endif %}{{ table.name | identifier }} (
{% for column in table.columns %}
    {{ column_definition(column) }}{% if not loop.last %},{% endif %}
{% endfor %}
{% if table.primary_key %}
    , PRIMARY KEY ({{ table.primary_key | map("identifier") | join(", ") }})
{% endif %}
{% for key in table.foreign_keys %}
    , FOREIGN KEY ({{ key.columns | map("identifier") | join(", ") }})
      REFERENCES {{ key.table | identifier }} ({{ key.references | map("identifier") | join(", ") }})
      ON DELETE {{ key.on_delete | upper }}
{% endfor %}
{% for columns in table.unique %}
    , UNIQUE ({{ columns | map("identifier") | join(", ") }})
{% endfor %}
{% for check in table.checks %}
    , CHECK ({{ predicate(check) }})
{% endfor %}
)
