from trove.render.simple_csv import TrovesearchSimpleCsvRenderer
from trove.render.rendering import SimpleRendering
from . import _base


# note: trovesearch only -- this renderer doesn't do arbitrary rdf

class TestSimpleCsvRenderer(_base.TrovesearchRendererTests):
    renderer_class = TrovesearchSimpleCsvRenderer
    expected_outputs = {
        'no_results': SimpleRendering(
            mediatype='text/csv',
            rendered_content='@id,sameAs,resourceType,resourceNature,title,name,dateCreated,dateModified,rights\r\n',
        ),
        'few_results': SimpleRendering(
            mediatype='text/csv',
            rendered_content=''.join((
                '@id,sameAs,resourceType,resourceNature,title,name,dateCreated,dateModified,rights\r\n',
                'http://blarg.example/vocab/anItem,,,,"an item, yes",,,,\r\n',
                'http://blarg.example/vocab/anItemm,,,,"an itemm, yes",,,,\r\n',
                'http://blarg.example/vocab/anItemmm,https://doi.example/13.0/anItemmm,,,"an itemmm, yes",,2001-02-03,,\r\n',
            )),
        ),
    }
