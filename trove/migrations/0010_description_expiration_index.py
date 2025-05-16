from django.db import migrations, models
from django.contrib.postgres.operations import AddIndexConcurrently


class Migration(migrations.Migration):
    atomic = False  # allow adding indexes concurrently (without locking tables)

    dependencies = [
        ('trove', '0009_resource_description_rename'),
    ]

    operations = [
        AddIndexConcurrently(
            model_name='latestresourcedescription',
            index=models.Index(fields=['expiration_date'], name='trove_lates_expirat_70dd04_idx'),
        ),
        AddIndexConcurrently(
            model_name='supplementaryresourcedescription',
            index=models.Index(fields=['expiration_date'], name='trove_suppl_expirat_3cb612_idx'),
        ),
    ]
