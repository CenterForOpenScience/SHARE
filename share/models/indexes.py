from django.db.models.indexes import Index


class ConcurrentIndex(Index):
    """Use Postgres' CONCURRENTLY to create a database index

    Migrations containing ConcurrentIndex creations must have "atomic = False"
    See https://www.postgresql.org/docs/current/static/sql-createindex.html#SQL-CREATEINDEX-CONCURRENTLY

    For the above reason it is recommened to have seperate migrations for index creation and schema changes
    """

    def create_sql(self, model, schema_editor, using=''):
        if schema_editor.atomic_migration:
            raise ValueError('Migrations creating concurrent indexes must have "atomic = False"')

        try:
            sql_create_index = schema_editor.sql_create_index_concurrently
        except AttributeError as e:
            raise ValueError('Concurrent index creation not supported by {}'.format(schema_editor)) from e

        sql_parameters = self.get_sql_create_template_values(model, schema_editor, using)
        return sql_create_index % sql_parameters
