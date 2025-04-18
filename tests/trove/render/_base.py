import json

from primitive_metadata import (
    gather,
    primitive_rdf as rdf,
)

from trove.trovesearch.trovesearch_gathering import trovesearch_by_indexstrategy
from trove.render._base import BaseRenderer
from trove.render._rendering import ProtoRendering
from trove.vocab.namespaces import RDF
from tests.trove._input_output_tests import BasicInputOutputTestCase
from ._inputs import UNRENDERED_RDF, UNRENDERED_SEARCH_RDF, RdfCase


class FakeGatherCache(gather._GatherCache):
    def already_gathered(self, *args, **kwargs):
        return True  # prevent gathering


class FakeGathering(gather.Gathering):
    def ask_exhaustively(self, *args, **kwargs):
        # skip exhaustion for these tests (note: only works for non-streaming)
        for _obj in self.ask(*args, **kwargs):
            yield (_obj, self.cache.gathered)


def _make_fake_gathering(tripledict, renderer_type):
    _organizer = trovesearch_by_indexstrategy
    _fakecache = FakeGatherCache()
    _fakecache.gathered = rdf.RdfGraph(tripledict)
    return FakeGathering(
        norms=_organizer.norms,
        organizer=_organizer,
        gatherer_kwargs={
            'deriver_iri': renderer_type.INDEXCARD_DERIVER_IRI,
        },
        cache=_fakecache,
    )


class TroveRendererTests(BasicInputOutputTestCase):
    inputs = UNRENDERED_RDF

    # required on subclasses: `renderer_class` and `expected_outputs`
    renderer_class: type[BaseRenderer]
    # expected_outputs: dict[str, typing.Any] (from BasicInputOutputTestCase)

    def compute_output(self, given_input: RdfCase):
        _renderer = self.renderer_class(
            response_focus=gather.Focus.new(
                given_input.focus,
                given_input.tripledict.get(given_input.focus, {}).get(RDF.type),
            ),
            response_gathering=_make_fake_gathering(given_input.tripledict, self.renderer_class),
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
