DROP FUNCTION {% if operation.if_exists %}IF EXISTS {% endif %}{{ operation.name | identifier }}()
