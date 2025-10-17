from __future__ import annotations
from email.utils import format_datetime as rfc2822_datetime
import itertools
import typing

from django.conf import settings
from django.utils.translation import gettext as _

from trove.render.rendering import EntireRendering
from trove.util.json import (
    json_datetimes,
    json_vals,
    json_strs,
)
from trove.util.xml import XmlBuilder
from trove.vocab import mediatypes
from ._trovesearch_card_only import TrovesearchCardOnlyRenderer

if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from trove.util.json import JsonObject
    from trove.render.rendering import ProtoRendering


class CardsearchRssRenderer(TrovesearchCardOnlyRenderer):
    '''render card-search results into RSS following https://www.rssboard.org/rss-specification
    '''
    MEDIATYPE = mediatypes.RSS

    def multicard_rendering(self, card_pages: Iterator[Sequence[tuple[str, JsonObject]]]) -> ProtoRendering:
        def _strs(*path: str) -> Iterator[str]:
            yield from json_strs(_osfmap_json, path, coerce_str=True)

        def _dates(*path: str) -> Iterator[str]:
            for _dt in json_datetimes(_osfmap_json, path):
                yield rfc2822_datetime(_dt)

        _xb = XmlBuilder('rss', {'version': '2.0'})
        with _xb.nest('channel'):
            # see https://www.rssboard.org/rss-specification#requiredChannelElements
            _xb.leaf('title', text=_('shtrove search results'))
            _xb.leaf('link', text=self.response_focus.single_iri())
            _xb.leaf('description', text=_('feed of metadata records matching given filters'))
            _xb.leaf('webMaster', text=settings.SHARE_SUPPORT_EMAIL)
            for _card_iri, _osfmap_json in itertools.chain.from_iterable(card_pages):
                with _xb.nest('item'):
                    # see https://www.rssboard.org/rss-specification#hrelementsOfLtitemgt
                    _iri = _osfmap_json.get('@id', _card_iri)
                    _xb.leaf('link', text=_iri)
                    _xb.leaf('guid', {'isPermaLink': 'true'}, text=_iri)
                    for _title in _strs('title'):
                        _xb.leaf('title', text=_title)
                    for _desc in _strs('description'):
                        _xb.leaf('description', text=_desc)
                    for _keyword in _strs('keyword'):
                        _xb.leaf('category', text=_keyword)
                    for _created_date in _dates('dateCreated'):
                        _xb.leaf('pubDate', text=_created_date)
                    for _creator_obj in json_vals(_osfmap_json, ['creator']):
                        assert isinstance(_creator_obj, dict)
                        _creator_name = next(json_strs(_creator_obj, ['name']))
                        _creator_id = _creator_obj.get('@id', _creator_name)
                        _xb.leaf('author', text=f'{_creator_id} ({_creator_name})')
        return EntireRendering(
            mediatype=self.MEDIATYPE,
            entire_content=bytes(_xb),
        )
