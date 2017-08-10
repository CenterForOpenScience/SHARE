from django.core.paginator import Paginator
from django.db import connections
from django.db.models.sql.datastructures import EmptyResultSet
from django.utils.functional import cached_property


class FuzzyPaginator(Paginator):

    @cached_property
    def count(self):
        cursor = connections[self.object_list.db].cursor()

        try:
            cursor.execute('SELECT count_estimate(%s);', (cursor.mogrify(*self.object_list.query.sql_with_params()).decode(), ))
        except EmptyResultSet:
            return 0

        return int(cursor.fetchone()[0])
