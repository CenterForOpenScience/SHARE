from django.conf import settings
from share.models.ingest import Source


def osf_sources():
    return Source.objects.filter(
        canonical=True,
    ).exclude(
        name='org.arxiv',
    ).exclude(
        user__username=settings.APPLICATION_USERNAME,
    )
