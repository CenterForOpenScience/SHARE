from django.db import migrations, models
from django.contrib.postgres.operations import AddIndexConcurrently


class Migration(migrations.Migration):
    atomic = False  # allow adding indexes concurrently (without locking tables)

    dependencies = [
        ('share', '0075_rawdatum_expiration_date'),
    ]

    operations = [
        AddIndexConcurrently(
            model_name='rawdatum',
            index=models.Index(fields=['expiration_date'], name='share_rawdatum_expiration_idx'),
        ),
    ]
