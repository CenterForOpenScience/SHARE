from django.db.backends.postgresql.schema import DatabaseSchemaEditor as PostgresDatabaseSchemaEditor

from db import deletion


class DatabaseSchemaEditor(PostgresDatabaseSchemaEditor):

    ON_DELETE_DEFAULT = 'NO ACTION'
    ON_UPDATE_DEFAULT = 'NO ACTION'

    sql_create_fk = (
        'ALTER TABLE {table} ADD CONSTRAINT {name} FOREIGN KEY ({column}) '
        'REFERENCES {to_table} ({to_column}) ON DELETE {on_delete} ON UPDATE {on_update}{deferrable}'  # deferrable happens to always have a space in front of it
    )

    def _create_fk_sql(self, model, field, suffix):
        from_table = model._meta.db_table
        from_column = field.column
        to_table = field.target_field.model._meta.db_table
        to_column = field.target_field.column
        suffix = suffix % {
            'to_table': to_table,
            'to_column': to_column,
        }

        return self.sql_create_fk.format(
            table=self.quote_name(from_table),
            name=self.quote_name(self._create_index_name(model, [from_column], suffix=suffix)),
            column=self.quote_name(from_column),
            to_table=self.quote_name(to_table),
            to_column=self.quote_name(to_column),
            on_delete=field.remote_field.on_delete.clause if isinstance(field.remote_field.on_delete, deletion.DatabaseOnDelete) else self.ON_DELETE_DEFAULT,
            on_update=field.remote_field.on_delete.clause if isinstance(field.remote_field.on_delete, deletion.DatabaseOnDelete) else self.ON_UPDATE_DEFAULT,
            deferrable=self.connection.ops.deferrable_sql(),
        )
