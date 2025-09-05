from trove.render.simple_tsv import TrovesearchSimpleTsvRenderer
from trove.render.rendering import SimpleRendering
from . import _base


# note: trovesearch only -- this renderer doesn't do arbitrary rdf

class TestSimpleTsvRenderer(_base.TrovesearchRendererTests):
    renderer_class = TrovesearchSimpleTsvRenderer
    expected_outputs = {
        'no_results': SimpleRendering(
            mediatype='text/tab-separated-values',
            rendered_content='@id\tsameAs\tresourceType\tresourceNature\ttitle\tname\tdateCreated\tdateModified\trights\r\n',
        ),
        'few_results': SimpleRendering(
            mediatype='text/tab-separated-values',
            rendered_content=''.join((
                '@id\tsameAs\tresourceType\tresourceNature\ttitle\tname\tdateCreated\tdateModified\trights\r\n',
                'http://blarg.example/vocab/anItem\t\t\t\tan item, yes\t\t\t\t\r\n',
                'http://blarg.example/vocab/anItemm\t\t\t\tan itemm, yes\t\t\t\t\r\n',
                'http://blarg.example/vocab/anItemmm\t\t\t\tan itemmm, yes\t\t\t\t\r\n',
            )),
        ),
    }
