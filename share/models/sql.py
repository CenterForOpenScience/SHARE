from django.db import models


class GroupBy(models.Aggregate):
    template = '%(expressions)s'

    def __init__(self, expression, **extra):
        super(GroupBy, self).__init__(
            expression,
            output_field=models.TextField(),
            **extra
        )

    def get_group_by_cols(self):
        return self.source_expressions
