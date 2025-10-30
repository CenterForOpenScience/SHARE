from unittest import mock
import datetime

from trove.render.cardsearch_atom import CardsearchAtomRenderer
from trove.render.rendering import EntireRendering
from . import _base


# note: cardsearch only -- this renderer doesn't do arbitrary rdf

class TestCardsearchAtomRenderer(_base.TrovesearchRendererTests):
    renderer_class = CardsearchAtomRenderer
    expected_outputs = {
        'no_results': EntireRendering(
            mediatype='application/atom+xml',
            entire_content=(
                b"<?xml version='1.0' encoding='utf-8'?>\n"
                b'<feed xmlns="http://www.w3.org/2005/Atom">'
                b'<title>shtrove search results</title>'
                b'<subtitle>feed of metadata records matching given filters</subtitle>'
                b'<link href="http://blarg.example/vocab/aSearch" />'
                b'<id>http://blarg.example/vocab/aSearch</id>'
                b'<updated>2345-06-07T08:09:10Z</updated>'
                b'</feed>'
            ),
        ),
        'few_results': EntireRendering(
            mediatype='application/atom+xml',
            entire_content=(
                b"<?xml version='1.0' encoding='utf-8'?>\n"
                b'<feed xmlns="http://www.w3.org/2005/Atom">'
                b'<title>shtrove search results</title>'
                b'<subtitle>feed of metadata records matching given filters</subtitle>'
                b'<link href="http://blarg.example/vocab/aSearchFew" />'
                b'<id>http://blarg.example/vocab/aSearchFew</id>'
                b'<updated>2345-06-07T08:09:10Z</updated>'
                b'<entry>'
                b'<link href="http://blarg.example/vocab/anItem" />'
                b'<id>http://blarg.example/vocab/aCard</id>'
                b'<title>an item, yes</title>'
                b'</entry><entry>'
                b'<link href="http://blarg.example/vocab/anItemm" />'
                b'<id>http://blarg.example/vocab/aCardd</id>'
                b'<title>an itemm, yes</title>'
                b'</entry><entry>'
                b'<link href="http://blarg.example/vocab/anItemmm" />'
                b'<id>http://blarg.example/vocab/aCarddd</id>'
                b'<title>an itemmm, yes</title>'
                b'<published>2001-02-03T00:00:00Z</published>'
                b'<author><name>a person indeed</name><uri>http://blarg.example/vocab/aPerson</uri></author>'
                b'</entry></feed>'
            ),
        ),
    }

    def setUp(self):
        self.enterContext(mock.patch(
            'django.utils.timezone.now',
            return_value=datetime.datetime(2345, 6, 7, 8, 9, 10, tzinfo=datetime.UTC),
        ))
