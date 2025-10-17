from trove.render.trovesearch_tsv import TrovesearchTsvRenderer
from trove.render.rendering import EntireRendering
from . import _base


# note: trovesearch only -- this renderer doesn't do arbitrary rdf

class TestTrovesearchTsvRenderer(_base.TrovesearchRendererTests):
    renderer_class = TrovesearchTsvRenderer
    expected_outputs = {
        'no_results': EntireRendering(
            mediatype='text/tab-separated-values',
            entire_content='@id\tsameAs\tresourceType\tresourceNature\ttitle\tname\tdateCreated\tdateModified\trights\r\n',
        ),
        'few_results': EntireRendering(
            mediatype='text/tab-separated-values',
            entire_content=''.join((
                '@id\tsameAs\tresourceType\tresourceNature\ttitle\tname\tdateCreated\tdateModified\trights\r\n',
                'http://blarg.example/vocab/anItem\t\t\t\tan item, yes\t\t\t\t\r\n',
                'http://blarg.example/vocab/anItemm\t\t\t\tan itemm, yes\t\t\t\t\r\n',
                'http://blarg.example/vocab/anItemmm\thttps://doi.example/13.0/anItemmm\t\t\tan itemmm, yes\t\t2001-02-03\t\t\r\n',
            )),
        ),
    }
