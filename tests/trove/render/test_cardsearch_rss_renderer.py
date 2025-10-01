from trove.render.cardsearch_rss import CardsearchRssRenderer
from trove.render.rendering import SimpleRendering
from . import _base


# note: cardsearch only -- this renderer doesn't do arbitrary rdf

class TestCardsearchRssRenderer(_base.TrovesearchRendererTests):
    renderer_class = CardsearchRssRenderer
    expected_outputs = {
        'no_results': SimpleRendering(
            mediatype='application/rss+xml',
            rendered_content=(
                b"<?xml version='1.0' encoding='utf-8'?>\n"
                b'<rss version="2.0">'
                b'<channel>'
                b'<title>shtrove search results</title>'
                b'<link>http://blarg.example/vocab/aSearch</link>'
                b'<description>feed of metadata records matching given filters</description>'
                b'<webMaster>share-support@cos.io</webMaster>'
                b'</channel></rss>'
            ),
        ),
        'few_results': SimpleRendering(
            mediatype='application/rss+xml',
            rendered_content=(
                b"<?xml version='1.0' encoding='utf-8'?>\n"
                b'<rss version="2.0"><channel>'
                b'<title>shtrove search results</title>'
                b'<link>http://blarg.example/vocab/aSearchFew</link>'
                b'<description>feed of metadata records matching given filters</description>'
                b'<webMaster>share-support@cos.io</webMaster>'
                b'<item>'
                b'<link>http://blarg.example/vocab/anItem</link>'
                b'<guid isPermaLink="true">http://blarg.example/vocab/anItem</guid>'
                b'<title>an item, yes</title>'
                b'</item><item>'
                b'<link>http://blarg.example/vocab/anItemm</link>'
                b'<guid isPermaLink="true">http://blarg.example/vocab/anItemm</guid>'
                b'<title>an itemm, yes</title>'
                b'</item><item>'
                b'<link>http://blarg.example/vocab/anItemmm</link>'
                b'<guid isPermaLink="true">http://blarg.example/vocab/anItemmm</guid>'
                b'<title>an itemmm, yes</title>'
                b'<pubDate>Sat, 03 Feb 2001 00:00:00 -0000</pubDate>'
                b'<author>http://blarg.example/vocab/aPerson (a person indeed)</author>'
                b'</item></channel></rss>'
            ),
        ),
    }
