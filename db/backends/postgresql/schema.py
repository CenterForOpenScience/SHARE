from django.db.backends.postgresql.schema import DatabaseSchemaEditor as PostgresDatabaseSchemaEditor

from db import deletion


class DatabaseSchemaEditor(PostgresDatabaseSchemaEditor):

    sql_create_index_concurrently = 'CREATE INDEX CONCURRENTLY %(name)s ON %(table)s%(using)s (%(columns)s)%(extra)s'
