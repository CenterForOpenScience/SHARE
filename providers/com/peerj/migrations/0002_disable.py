from django.db import migrations
import share.robot


class Migration(migrations.Migration):

    dependencies = [
        ('com.peerj', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            code=share.robot.DisableRobotScheduleMigration('com.peerj'),
        ),
    ]
