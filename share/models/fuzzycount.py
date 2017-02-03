from django.db import connections
from django.db.models import QuerySet, Manager


class FuzzyCountQuerySet(QuerySet):
    def count(self):
        cursor = connections[self.db].cursor()
        cursor.execute('SELECT count_estimate(%s);', (cursor.mogrify(*self.query.sql_with_params()).decode(), ))
        return int(cursor.fetchone()[0])

    def exact_count(self):
        return super().count()

FuzzyCountManager = Manager.from_queryset(FuzzyCountQuerySet)
