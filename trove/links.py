import dataclasses
import urllib.parse

from django.conf import settings
from django.http import QueryDict
from django.urls import reverse

from trove.vocab.namespaces import namespaces_shorthand


def is_local_url(iri: str) -> bool:
    return iri.startswith(settings.SHARE_WEB_URL)


def trove_browse_link(iri: str) -> str:
    return reverse(
        'trove:browse-iri',
        query={
            'blendCards': True,
            'iri': namespaces_shorthand().compact_iri(iri),
        },
    )


@dataclasses.dataclass
class FeedLinks:
    rss: str
    atom: str


def cardsearch_feed_links(cardsearch_iri: str) -> FeedLinks | None:
    _split_iri = urllib.parse.urlsplit(cardsearch_iri)
    if _split_iri.path != reverse('trove:index-card-search'):
        return None
    _feed_query = _get_feed_query(_split_iri.query)
    _rss_link = urllib.parse.urljoin(
        settings.SHARE_WEB_URL,
        reverse('trove:cardsearch-rss', query=_feed_query)
    )
    _atom_link = urllib.parse.urljoin(
        settings.SHARE_WEB_URL,
        reverse('trove:cardsearch-atom', query=_feed_query)
    )
    return FeedLinks(rss=_rss_link, atom=_atom_link)


def _get_feed_query(query_string: str) -> QueryDict:
    _qparams = QueryDict(query_string, mutable=True)
    for _param_name in list(filter(_irrelevant_feed_param, _qparams.keys())):
        del _qparams[_param_name]
    return _qparams


def _irrelevant_feed_param(query_param_name: str) -> bool:
    return (
        query_param_name in ('sort', 'include', 'acceptMediatype', 'blendCards', 'page[cursor]')
        or query_param_name.startswith('fields')
    )
