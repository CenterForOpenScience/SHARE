from trove.render.simple_csv import TrovesearchSimpleCsvRenderer
from trove.render.rendering import EntireRendering
from . import _base


# note: trovesearch only -- this renderer doesn't do arbitrary rdf

class TestSimpleCsvRenderer(_base.TrovesearchRendererTests):
    renderer_class = TrovesearchSimpleCsvRenderer
    expected_outputs = {
        'no_results': EntireRendering(
            mediatype='text/csv',
            entire_content='@id,sameAs,resourceType,resourceNature,title,name,dateCreated,dateModified,rights\r\n',
        ),
        'few_results': EntireRendering(
            mediatype='text/csv',
            entire_content=''.join((
                '@id,sameAs,resourceType,resourceNature,title,name,dateCreated,dateModified,rights\r\n',
                'http://blarg.example/vocab/anItem,,,,"an item, yes",,,,\r\n',
                'http://blarg.example/vocab/anItemm,,,,"an itemm, yes",,,,\r\n',
                'http://blarg.example/vocab/anItemmm,https://doi.example/13.0/anItemmm,,,"an itemmm, yes",,2001-02-03,,\r\n',
            )),
        ),
    }
