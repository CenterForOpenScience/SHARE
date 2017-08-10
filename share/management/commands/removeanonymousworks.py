from django.core.management.base import BaseCommand
from django.db.models import Exists
from django.db.models import OuterRef

from share.search import SearchIndexer

from project import celery_app

from share.models import WorkIdentifier
from share.models import AbstractCreativeWork


class Command(BaseCommand):

    def handle(self, *args, **options):
        qs = AbstractCreativeWork.objects.annotate(
            has_identifiers=Exists(
                WorkIdentifier.objects.filter(creative_work=OuterRef('pk'))
            )
        ).exclude(has_identifiers=True)

        indexer = SearchIndexer(celery_app)

        print(qs.query)
        for id in qs.values_list('id', flat=True).iterator():
            indexer.index('creativework', id)
