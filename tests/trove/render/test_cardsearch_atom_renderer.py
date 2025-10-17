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
                b'<link>http://blarg.example/vocab/aSearch</link>'
                b'<id>http://blarg.example/vocab/aSearch</id>'
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
                b'<link>http://blarg.example/vocab/aSearchFew</link>'
                b'<id>http://blarg.example/vocab/aSearchFew</id>'
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
                b'</entry></feed>'
            ),
        ),
    }
