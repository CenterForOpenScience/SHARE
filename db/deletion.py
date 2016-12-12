"""Force django to use the ON DELETE/ON UPDATE clauses when making foreign keys
NOTE: delete hooks for cascaded objects WILL NOT be run
"""
from django.db.models.deletion import DO_NOTHING


class DatabaseOnDelete:

    def __init__(self, clause='NO ACTION'):
        self.clause = clause

    def __call__(self, collector, field, sub_objs, using):
        pass

    def __eq__(self, other):
        # Feign equility with DO_NOTHING so Django doesn't try to do anything clever
        return DO_NOTHING == other or (isinstance(other, DatabaseOnDelete) and other.clause == self.clause)

    def deconstruct(self):
        return '{}.{}'.format(__name__, type(self).__name__), (), {'clause': self.clause}


DATABASE_CASCADE = DatabaseOnDelete('CASCADE')
DATABASE_RESTRICT = DatabaseOnDelete('RESTRICT')
DATABASE_SET_DEFAULT = DatabaseOnDelete('SET DEFAULT')
DATABASE_SET_NULL = DatabaseOnDelete('SET NULL')
