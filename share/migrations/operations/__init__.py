from django.db import migrations


class AlterIndexTogetherConcurrent(migrations.AlterIndexTogether):

    atomic = False
    # option_name = 'index_together_current'
