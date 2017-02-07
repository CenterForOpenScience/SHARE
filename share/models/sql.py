from django.db import connections
from django.db.models.sql import InsertQuery
from django.db.models.sql.compiler import SQLInsertCompiler

from share.models.fuzzycount import FuzzyCountManager
from share.models.fuzzycount import FuzzyCountQuerySet


class SQLInsertReturnVersionCompiler(SQLInsertCompiler):

    def as_sql(self):
        # We don't need quote_name_unless_alias() here, since these are all
        # going to be column names (so we can avoid the extra overhead).
        qn = self.connection.ops.quote_name
        opts = self.query.get_meta()
        result = ['INSERT INTO %s' % qn(opts.db_table)]

        has_fields = bool(self.query.fields)
        fields = self.query.fields if has_fields else [opts.pk]
        result.append('(%s)' % ', '.join(qn(f.column) for f in fields))

        if has_fields:
            value_rows = [
                [self.prepare_value(field, self.pre_save_val(field, obj)) for field in fields]
                for obj in self.query.objs
            ]
        else:
            # An empty object.
            value_rows = [[self.connection.ops.pk_default_value()] for _ in self.query.objs]
            fields = [None]

        # Currently the backends just accept values when generating bulk
        # queries and generate their own placeholders. Doing that isn't
        # necessary and it should be possible to use placeholders and
        # expressions in bulk inserts too.
        can_bulk = (not self.return_id and self.connection.features.has_bulk_insert)

        placeholder_rows, param_rows = self.assemble_as_sql(fields, value_rows)

        if self.return_id and self.connection.features.can_return_id_from_insert:
            params = param_rows[0]
            result.append("VALUES (%s)" % ", ".join(placeholder_rows[0]))

            ### ACTUAL CHANGE HERE ###
            result.append('RETURNING ("{0}"."{1}", "{0}"."{2}")'.format(opts.db_table, opts.pk.column, opts.get_field('version').column))
            ### /ACTUAL CHANGE HERE ###

            return [(" ".join(result), tuple(params))]

        if can_bulk:
            result.append(self.connection.ops.bulk_insert_sql(fields, placeholder_rows))
            return [(" ".join(result), tuple(p for ps in param_rows for p in ps))]
        else:
            return [
                (" ".join(result + ["VALUES (%s)" % ", ".join(p)]), vals)
                for p, vals in zip(placeholder_rows, param_rows)
            ]


class InsertReturnVersionQuery(InsertQuery):

    def get_compiler(self, using=None, connection=None):
        if using is None and connection is None:
            raise ValueError("Need either using or connection")
        if using:
            connection = connections[using]
        return SQLInsertReturnVersionCompiler(self, connection, using)


class InsertReturnVersionQuerySet(FuzzyCountQuerySet):

    def _insert(self, objs, fields, return_id=False, raw=False, using=None):
        """
        Inserts a new record for the given model. This provides an interface to
        the InsertQuery class and is how Model.save() is implemented.
        """
        self._for_write = True
        if using is None:
            using = self.db
        query = InsertReturnVersionQuery(self.model)
        query.insert_values(fields, objs, raw=raw)
        return query.get_compiler(using=using).execute_sql(return_id)
    _insert.alters_data = True
    _insert.queryset_only = False


class CircularMergeError(Exception):
    pass


class ShareObjectManager(FuzzyCountManager):
    use_for_related_fields = True

    def get_queryset(self):
        return InsertReturnVersionQuerySet(self.model, using=self._db)

    def get_canonical(self, id):
        query = '''
        WITH RECURSIVE same_as_chain(id, same_as, depth, path, cycle) AS (
                SELECT id, same_as_id, 1, ARRAY[id], false FROM {table} WHERE id = %(id)s
              UNION
                SELECT {table}.id, {table}.same_as_id, same_as_chain.depth + 1, path || {table}.id, {table}.id = ANY(path)
                FROM same_as_chain JOIN {table} ON same_as_chain.same_as = {table}.id
                WHERE NOT cycle
        )
        SELECT * FROM {table} WHERE id=(SELECT id FROM same_as_chain ORDER BY depth DESC LIMIT 1);
        '''.format(table=self.model._meta.db_table)

        results = self.model._meta.concrete_model.objects.raw(query, params={'id': id})
        if not results:
            return None
        result = results[0]
        if result.same_as_id is not None:
            raise CircularMergeError('Reference loop in %s.same_as (frow row %s to %s)', self.model._meta.db_table, id, result.id)
        return result
