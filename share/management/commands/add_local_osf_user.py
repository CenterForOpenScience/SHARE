from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from share.models import ShareUser, Source
from share.management.commands import BaseShareCommand


class Command(BaseShareCommand):
    def add_arguments(self, parser):
        parser.add_argument('--name', default='my-local-osf')

    def handle(self, *args, **options):
        user = ShareUser.objects.create_robot_user(
            username=options['name'],
            robot=options['name'],
            is_trusted=True,
        )
        content_type = ContentType.objects.get_for_model(Source)
        add_source_permission = Permission.objects.get(
            content_type=content_type,
            codename='add_source',
        )
        user.user_permissions.add(add_source_permission)
        access_token = user.oauth2_provider_accesstoken.first().token
        self.stdout.write(self.style.SUCCESS(f'added user "{user.username}" for local osf'))
        self.stdout.write(f'access-token: {access_token}')
