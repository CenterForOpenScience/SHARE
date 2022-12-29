import re

from django.conf import settings

from share.util.graph import MutableGraph
from share.util import rdfutil


def osf_sources():
    from share.models.ingest import Source
    return Source.objects.filter(
        canonical=True,
    ).exclude(
        name='org.arxiv',
    ).exclude(
        user__username=settings.APPLICATION_USERNAME,
    )


OSF_BARE_GUID_RE = re.compile(r'[a-z0-9]{5,7}')

OSF_GUID_URI_RE = re.compile(r'^https?://(?:[^.]+\.)?osf\.io/(?P<guid>[^/]+)/?$')


def maybe_osfguid_uri(maybe_bare_guid):
    if not isinstance(maybe_bare_guid, str):
        return None
    maybe_bare_guid = maybe_bare_guid.strip().lower()
    if OSF_BARE_GUID_RE.fullmatch(maybe_bare_guid):
        return rdfutil.OSFIO[maybe_bare_guid]


def get_guid_from_uri(uri: str):
    match = OSF_GUID_URI_RE.match(uri)
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
