from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('trove', '0009_no_raw_datum'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ArchivedIndexcardRdf',
            new_name='ArchivedResourceDescription',
        ),
        migrations.RenameModel(
            old_name='LatestIndexcardRdf',
            new_name='LatestResourceDescription',
        ),
        migrations.RenameModel(
            old_name='SupplementaryIndexcardRdf',
            new_name='SupplementaryResourceDescription',
        ),
        migrations.AlterField(
            model_name='archivedresourcedescription',
            name='indexcard',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trove_archivedresourcedescription_set', to='trove.indexcard'),
        ),
        migrations.AlterField(
            model_name='latestresourcedescription',
            name='indexcard',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trove_latestresourcedescription_set', to='trove.indexcard'),
        ),
        migrations.AlterField(
            model_name='supplementaryresourcedescription',
            name='indexcard',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trove_supplementaryresourcedescription_set', to='trove.indexcard'),
        ),
        migrations.AlterField(
            model_name='supplementaryresourcedescription',
            name='supplementary_suid',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='supplementary_description_set', to='share.sourceuniqueidentifier'),
        ),
    ]
