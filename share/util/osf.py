import re

from django.conf import settings

from share.models.ingest import Source
from share.util.graph import MutableGraph


def osf_sources():
    return Source.objects.filter(
        canonical=True,
    ).exclude(
        name='org.arxiv',
    ).exclude(
        user__username=settings.APPLICATION_USERNAME,
    )


OSF_GUID_RE = re.compile(r'^https?://(?:[^.]+\.)?osf\.io/(?P<guid>[^/]+)/?$')


def get_guid_from_uri(uri: str):
    match = OSF_GUID_RE.match(uri)
    return match.group('guid') if match else None


def guess_osf_guid(mgraph: MutableGraph):
    central_work = mgraph.get_central_node(guess=True)
    if not central_work:
        return None

    osf_guids = list(filter(bool, (
        get_guid_from_uri(identifier['uri'])
        for identifier in central_work['identifiers']
    )))
    # if >1, too ambiguous
    if len(osf_guids) == 1:
        return osf_guids[0]
    return None
