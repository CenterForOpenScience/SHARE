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
            response_focus_iri=given_input.focus,
            response_tripledict=given_input.tripledict,
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

    def missing_case_message(self, name: str, given_input) -> str:
        _cls = self.__class__
        _actual_output = self.compute_output(given_input)
        return '\n'.join((
            super().missing_case_message(name, given_input)
            'missing test case!',
            f'\tadd "{name}" to {_cls.__module__}.{_cls.__qualname__}.expected_outputs',
            '\tactual output, fwiw:',
            self._get_rendered_output(_actual_output)
        )))

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
