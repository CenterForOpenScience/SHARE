from django.db import migrations
import share.robot


class Migration(migrations.Migration):

    dependencies = [
        ('com.figshare', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            code=share.robot.DisableRobotScheduleMigration('com.figshare'),
        ),
    ]
