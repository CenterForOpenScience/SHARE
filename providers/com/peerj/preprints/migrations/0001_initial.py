from django.db import migrations
import share.robot


class Migration(migrations.Migration):

    dependencies = [
        ('share', '0001_initial'),
        ('com.peerj', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            code=share.robot.RobotScheduleMigration('com.peerj.preprints'),
        ),
    ]
