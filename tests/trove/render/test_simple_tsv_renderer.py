from trove.render.simple_tsv import TrovesearchSimpleTsvRenderer
from trove.render._rendering import SimpleRendering
from . import _base


# note: trovesearch only -- this renderer doesn't do arbitrary rdf

class TestSimpleTsvRenderer(_base.TrovesearchRendererTests):
    renderer_class = TrovesearchSimpleTsvRenderer
    expected_outputs = {
        'no_results': SimpleRendering(
            mediatype='text/tab-separated-values',
            rendered_content='@id\r\n',
        ),
        'few_results': SimpleRendering(
            mediatype='text/tab-separated-values',
            rendered_content=''.join((
                '@id\ttitle\r\n',
                'http://blarg.example/vocab/anItem\tan item, yes\r\n',
                'http://blarg.example/vocab/anItemm\tan itemm, yes\r\n',
                'http://blarg.example/vocab/anItemmm\tan itemmm, yes\r\n',
            )),
        ),
    }
