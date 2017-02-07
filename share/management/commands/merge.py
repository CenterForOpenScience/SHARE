from django.core.management.base import BaseCommand
from django.conf import settings

from share.models import ShareUser, NormalizedData
from share.tasks import DisambiguatorTask
from share.util import IDObfuscator


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('from', nargs='*', type=str, help='The SHARE IDs of the objects to merge')
        parser.add_argument('--into', type=str, help='The SHARE ID of the object to merge into')
        parser.add_argument('--async', action='store_true', help='Whether or not to use Celery')

    def handle(self, *args, **options):
        user = ShareUser.objects.get(username=settings.APPLICATION_USERNAME)

        into_id = options['into']
        into = IDObfuscator.load(into_id)

        nodes = []
        for id in options['from']:
            from_obj = IDObfuscator.load(id)
            nodes.append({
                '@id': id,
                '@type': from_obj._meta.model_name,
                'same_as': {'@id': into_id, '@type': into._meta.model_name}
            })

        normalized = NormalizedData(source=user, data={'@graph': nodes})
        normalized.save()
        task_args = (user.id, normalized.id)
        if options['async']:
            DisambiguatorTask().apply_async(task_args)
        else:
            DisambiguatorTask().apply(task_args, throw=True)
