from django.db.backends.postgresql.base import DatabaseWrapper as PostgresqlDatabaseWrapper

from db.backends.postgresql.creation import DatabaseCreation
from db.backends.postgresql.schema import DatabaseSchemaEditor


class DatabaseWrapper(PostgresqlDatabaseWrapper):
    creation_class = DatabaseCreation
    SchemaEditorClass = DatabaseSchemaEditor
