import html
import typing

from trove.render.html_browse import RdfHtmlBrowseRenderer
from . import _base


# note: smoke tests only (TODO: better)

class TestTrovesearchHtmlRenderer(_base.TrovesearchRendererTests):
    renderer_class = RdfHtmlBrowseRenderer
    expected_outputs = {
        'no_results': {
            'mediatype': 'text/html',
            'result_iris': [],
        },
        'few_results': {
            'mediatype': 'text/html',
            'result_iris': [
                'http://blarg.example/vocab/anItem',
                'http://blarg.example/vocab/anItemm',
                'http://blarg.example/vocab/anItemmm',
            ],
        },
    }

    def assert_outputs_equal(self, expected_output: typing.Any, actual_output: typing.Any) -> None:
        self.assertEqual(actual_output.mediatype, expected_output['mediatype'])
        # smoke tests -- instead of asserting full rendered html page, just check the results are in there
        for _result_iri in expected_output['result_iris']:
            self.assertIn(html.escape(_result_iri), actual_output.entire_content)
