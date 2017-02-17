from django.db import connections
from django.db.backends.postgresql.creation import DatabaseCreation as PostgresqlDatabaseCreation


class DatabaseCreation(PostgresqlDatabaseCreation):

    def _destroy_test_db(self, test_database_name, verbosity):
        for connection in connections.all():
            if connection.settings_dict['TEST']['MIRROR'] and connection.settings_dict['TEST']['NAME'] == test_database_name:
                connection.close()
        return super()._destroy_test_db(test_database_name, verbosity)
