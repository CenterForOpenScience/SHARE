from django.db import migrations
import share.robot


class Migration(migrations.Migration):

    dependencies = [
        ('org.zenodo', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            code=share.robot.DisableRobotScheduleMigration('org.zenodo'),
        ),
    ]
