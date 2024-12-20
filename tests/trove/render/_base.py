import json

from trove.render._base import BaseRenderer
from trove.render._rendering import ProtoRendering
from tests.trove._input_output_tests import BasicInputOutputTestCase
from ._inputs import UNRENDERED_RDF, UNRENDERED_SEARCH_RDF, RdfCase


class TroveRendererTests(BasicInputOutputTestCase):
    inputs = UNRENDERED_RDF

    # required on subclasses: `renderer_class` and `expected_outputs`
    renderer_class: type[BaseRenderer]
    # expected_outputs: dict[str, typing.Any] (from BasicInputOutputTestCase)

    def compute_output(self, given_input: RdfCase):
        _renderer = self.renderer_class(
            response_focus=given_input.focus,
            response_gathering=...,
        )
        return _renderer.render_document()

    def assert_outputs_equal(self, expected_output, actual_output) -> None:
        if expected_output is None:
            print(repr(actual_output))
            raise NotImplementedError
        self.assertEqual(expected_output.mediatype, actual_output.mediatype)
        self.assertEqual(
            self._get_rendered_output(expected_output),
            self._get_rendered_output(actual_output),
        )

    def _get_rendered_output(self, rendering: ProtoRendering):
        # for now, they always iter strings (update if/when bytes are in play)
        return ''.join(rendering.iter_content())  # type: ignore[arg-type]


class TrovesearchRendererTests(TroveRendererTests):
    inputs = UNRENDERED_SEARCH_RDF


class TroveJsonRendererTests(TroveRendererTests):
    def _get_rendered_output(self, rendering: ProtoRendering):
        return json.loads(super()._get_rendered_output(rendering))


class TrovesearchJsonRendererTests(TroveJsonRendererTests, TrovesearchRendererTests):
    pass
