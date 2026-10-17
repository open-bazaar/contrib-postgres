ALTER TABLE {{ operation.table | identifier }} RENAME COLUMN {{ operation.column | identifier }} TO {{ operation.name | identifier }}
