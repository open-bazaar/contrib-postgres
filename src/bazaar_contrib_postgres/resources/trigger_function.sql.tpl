{% from "fragments.sql.tpl" import predicate with context %}
CREATE FUNCTION {{ operation.name | identifier }}() RETURNS trigger LANGUAGE plpgsql AS $trigger$
BEGIN
    {% set request = operation.action %}
    {% include "update.sql.tpl" %};
    RETURN NULL;
END
$trigger$
