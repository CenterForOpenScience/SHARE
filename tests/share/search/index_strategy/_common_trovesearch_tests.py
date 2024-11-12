from typing import Iterable, Iterator
from datetime import date, timedelta
import itertools
import math
from urllib.parse import urlencode

from primitive_metadata import primitive_rdf as rdf

from tests import factories
from share.search import messages
from trove import models as trove_db
from trove.trovesearch.search_params import CardsearchParams, ValuesearchParams
from trove.vocab.namespaces import RDFS, TROVE, RDF, DCTERMS, OWL, FOAF, DCAT
from ._with_real_services import RealElasticTestCase


BLARG = rdf.IriNamespace('https://blarg.example/blarg/')


class CommonTrovesearchTests(RealElasticTestCase):
    _indexcard_focus_by_uuid: dict[str, str]

    def setUp(self):
        super().setUp()
        self._indexcard_focus_by_uuid = {}

    def test_for_smoke_without_daemon(self):
        _indexcard = self._create_indexcard(
            focus_iri=BLARG.hello,
            rdf_tripledict={BLARG.hello: {RDFS.label: {rdf.literal('hello')}}},
        )
        _messages_chunk = messages.MessagesChunk(
            messages.MessageType.UPDATE_INDEXCARD,
            [_indexcard.id],
        )
        self._assert_happypath_without_daemon(
            _messages_chunk,
            expected_doc_count=1,
        )

    def test_for_smoke_with_daemon(self):
        _indexcard = self._create_indexcard(
            focus_iri=BLARG.hello,
            rdf_tripledict={BLARG.hello: {RDFS.label: {rdf.literal('hello')}}},
        )
        _messages_chunk = messages.MessagesChunk(
            messages.MessageType.UPDATE_INDEXCARD,
            [_indexcard.id],
        )
        self._assert_happypath_with_daemon(
            _messages_chunk,
            expected_doc_count=1,
        )

    def test_cardsearch(self):
        self._fill_test_data_for_querying()
        _cardsearch_cases = itertools.chain(
            self.cardsearch_cases(),
            self.cardsearch_integer_cases(),
        )
        for _queryparams, _expected_result_iris in _cardsearch_cases:
            _cardsearch_params = CardsearchParams.from_querystring(urlencode(_queryparams))
            assert isinstance(_cardsearch_params, CardsearchParams)
            _cardsearch_response = self.current_index.pls_handle_cardsearch(_cardsearch_params)
            # assumes all results fit on one page
            _actual_result_iris: set[str] | list[str] = [
                self._indexcard_focus_by_uuid[_result.card_uuid]
                for _result in _cardsearch_response.search_result_page
            ]
            # test sort order only when expected results are ordered
            if isinstance(_expected_result_iris, set):
                _actual_result_iris = set(_actual_result_iris)
            self.assertEqual(_expected_result_iris, _actual_result_iris, msg=f'?{_queryparams}')

    def test_cardsearch_pagination(self):
        _cards: list[trove_db.Indexcard] = []
        _expected_iris = set()
        _page_size = 7
        _total_count = 55
        _start_date = date(1999, 12, 31)
        for _i in range(_total_count):
            _card_iri = BLARG[f'i{_i}']
            _expected_iris.add(_card_iri)
            _cards.append(self._create_indexcard(_card_iri, {
                _card_iri: {
                    RDF.type: {BLARG.Thing},
                    DCTERMS.title: {rdf.literal(f'card #{_i}')},
                    DCTERMS.created: {rdf.literal(_start_date + timedelta(weeks=_i, days=_i))},
                },
            }))
        self._index_indexcards(_cards)
        # gather all pages results:
        _querystring: str = f'page[size]={_page_size}'
        _result_iris: set[str] = set()
        _page_count = 0
        while True:
            _cardsearch_response = self.current_index.pls_handle_cardsearch(
                CardsearchParams.from_querystring(_querystring),
            )
            _page_iris = {
                self._indexcard_focus_by_uuid[_result.card_uuid]
                for _result in _cardsearch_response.search_result_page
            }
            self.assertFalse(_result_iris.intersection(_page_iris))
            self.assertLessEqual(len(_page_iris), _page_size)
            _result_iris.update(_page_iris)
            _page_count += 1
            _next_cursor = _cardsearch_response.cursor.next_cursor()
            if _next_cursor is None:
                break
            _querystring = urlencode({'page[cursor]': _next_cursor.as_queryparam_value()})
        self.assertEqual(_page_count, math.ceil(_total_count / _page_size))
        self.assertEqual(_result_iris, _expected_iris)

    def test_valuesearch(self):
        self._fill_test_data_for_querying()
        _valuesearch_cases = itertools.chain(
            self.valuesearch_simple_cases(),
            self.valuesearch_complex_cases(),
        )
        for _queryparams, _expected_values in _valuesearch_cases:
            _valuesearch_params = ValuesearchParams.from_querystring(urlencode(_queryparams))
            assert isinstance(_valuesearch_params, ValuesearchParams)
            _valuesearch_response = self.current_index.pls_handle_valuesearch(_valuesearch_params)
            # assumes all results fit on one page
            _actual_values = {
                _result.value_iri or _result.value_value
                for _result in _valuesearch_response.search_result_page
            }
            self.assertEqual(_expected_values, _actual_values)

    def _fill_test_data_for_querying(self):
        _card_a = self._create_indexcard(BLARG.a, {
            BLARG.a: {
                RDF.type: {BLARG.Thing},
                OWL.sameAs: {BLARG.a_same, BLARG.a_same2},
                DCTERMS.created: {rdf.literal(date(1999, 12, 31))},
                DCTERMS.creator: {BLARG.someone},
                DCTERMS.title: {rdf.literal('aaaa')},
                DCTERMS.subject: {BLARG.subj_ac, BLARG.subj_a},
                DCTERMS.references: {BLARG.b, BLARG.c},
                DCTERMS.description: {rdf.literal('This place is not a place of honor... no highly esteemed deed is commemorated here... nothing valued is here.', language='en')},
            },
            BLARG.someone: {
                FOAF.name: {rdf.literal('some one')},
            },
            BLARG.b: {
                RDF.type: {BLARG.Thing},
                DCTERMS.subject: {BLARG.subj_b, BLARG.subj_bc},
                DCTERMS.title: {rdf.literal('bbbb')},
                DCTERMS.references: {BLARG.c},
            },
            BLARG.c: {
                RDF.type: {BLARG.Thing},
                DCTERMS.subject: {BLARG.subj_ac, BLARG.subj_bc},
                DCTERMS.title: {rdf.literal('cccc')},
            },
        })
        _card_b = self._create_indexcard(BLARG.b, {
            BLARG.b: {
                RDF.type: {BLARG.Thing},
                OWL.sameAs: {BLARG.b_same},
                DCTERMS.created: {rdf.literal(date(2012, 12, 31))},
                DCTERMS.creator: {BLARG.someone},
                DCTERMS.title: {rdf.literal('bbbb')},
                DCTERMS.subject: {BLARG.subj_b, BLARG.subj_bc},
                DCTERMS.references: {BLARG.c},
                DCTERMS.description: {rdf.literal('What is here was dangerous and repulsive to us. This message is a warning about danger. ', language='en')},
            },
            BLARG.someone: {
                FOAF.name: {rdf.literal('some one')},
            },
            BLARG.c: {
                RDF.type: {BLARG.Thing},
                DCTERMS.subject: {BLARG.subj_ac, BLARG.subj_bc},
                DCTERMS.title: {rdf.literal('cccc')},
            },
        })
        _card_c = self._create_indexcard(BLARG.c, {
            BLARG.c: {
                RDF.type: {BLARG.Thing},
                DCTERMS.created: {rdf.literal(date(2024, 12, 31))},
                DCTERMS.creator: {BLARG.someone_else},
                DCTERMS.title: {rdf.literal('cccc')},
                DCTERMS.subject: {BLARG.subj_ac, BLARG.subj_bc},
                DCTERMS.description: {rdf.literal('The danger is unleashed only if you substantially disturb this place physically. This place is best shunned and left uninhabited.', language='en')},
            },
            BLARG.someone_else: {
                FOAF.name: {rdf.literal('some one else')},
            },
        })
        self._create_supplement(_card_a, BLARG.a, {
            BLARG.a: {
                DCTERMS.replaces: {BLARG.a_past},
                DCAT.servesDataset: {
                    rdf.blanknode({DCAT.spatialResolutionInMeters: {rdf.literal(10)}}),
                },
            },
        })
        self._create_supplement(_card_b, BLARG.b, {
            BLARG.b: {
                DCTERMS.replaces: {BLARG.b_past},
                DCAT.servesDataset: {
                    rdf.blanknode({DCAT.spatialResolutionInMeters: {rdf.literal(7)}}),
                },
            },
        })
        self._create_supplement(_card_c, BLARG.c, {
            BLARG.c: {
                DCTERMS.replaces: {BLARG.c_past},
                DCAT.servesDataset: {
                    rdf.blanknode({DCAT.spatialResolutionInMeters: {rdf.literal(333)}}),
                },
            },
        })
        self._index_indexcards([_card_a, _card_b, _card_c])

    def cardsearch_cases(self) -> Iterator[tuple[dict[str, str], set[str] | list[str]]]:
        # using data from _fill_test_data_for_querying
        yield (
            {},  # no query params
            {BLARG.a, BLARG.b, BLARG.c},
        )
        yield (
            {'sort': 'dateCreated'},
            [BLARG.a, BLARG.b, BLARG.c],  # ordered list
        )
        yield (
            {'sort': '-dateCreated'},
            [BLARG.c, BLARG.b, BLARG.a],  # ordered list
        )
        yield (
            {'cardSearchFilter[creator]': BLARG.someone},
            {BLARG.a, BLARG.b},
        )
        yield (
            {'cardSearchFilter[creator]': ','.join((BLARG.someone_else, BLARG.someone))},
            {BLARG.a, BLARG.b, BLARG.c},
        )
        yield (
            {'cardSearchFilter[resourceType]': BLARG.Thing},
            {BLARG.a, BLARG.b, BLARG.c},
        )
        yield (
            {'cardSearchFilter[resourceType]': BLARG.Nothing},
            set(),
        )
        yield (
            {'cardSearchFilter[references]': BLARG.b},
            {BLARG.a},
        )
        yield (
            {'cardSearchFilter[references]': BLARG.c},
            {BLARG.a, BLARG.b},
        )
        yield (
            {'cardSearchFilter[references.references]': BLARG.c},
            {BLARG.a},
        )
        yield (
            {'cardSearchFilter[references.references][is-present]': ''},
            {BLARG.a},
        )
        yield (
            {'cardSearchFilter[references.references.subject][is-present]': ''},
            {BLARG.a},
        )
        yield (
            {'cardSearchFilter[references.references][is-absent]': ''},
            {BLARG.c, BLARG.b},
        )
        yield (
            {'cardSearchFilter[references.references.subject][is-absent]': ''},
            {BLARG.c, BLARG.b},
        )
        yield (
            {'cardSearchFilter[dcterms:replaces]': BLARG.b_past},
            {BLARG.b},
        )
        yield (
            {'cardSearchFilter[dcterms:replaces][is-absent]': ''},
            set(),
        )
        yield (
            {'cardSearchFilter[subject]': BLARG.subj_ac},
            {BLARG.c, BLARG.a},
        )
        yield (
            {'cardSearchFilter[subject][none-of]': BLARG.subj_ac},
            {BLARG.b},
        )
        yield (
            {
                'cardSearchFilter[subject]': BLARG.subj_bc,
                'cardSearchFilter[creator]': BLARG.someone,
            },
            {BLARG.b},
        )
        yield (
            {
                'cardSearchFilter[subject]': BLARG.subj_bc,
                'cardSearchText[*]': 'cccc',
            },
            {BLARG.c},
        )
        yield (
            {
                'cardSearchFilter[resourceType]': ','.join((BLARG.Thing, BLARG.Another, BLARG.Nothing)),
                'cardSearchFilter[subject]': BLARG.subj_bc,
                'cardSearchText[*,creator.name]': 'else',
            },
            {BLARG.c},
        )
        yield (
            {
                'cardSearchFilter[resourceType]': BLARG.Nothing,
                'cardSearchFilter[subject]': BLARG.subj_bc,
                'cardSearchText[*,creator.name]': 'else',
            },
            set(),
        )
        yield (
            {'cardSearchText[*,creator.name]': 'some'},
            {BLARG.a, BLARG.b, BLARG.c},
        )
        yield (
            {
                'cardSearchFilter[dateCreated]': '1999',
                'cardSearchText[*]': '',
            },
            {BLARG.a},
        )
        yield (
            {'cardSearchFilter[dateCreated]': '1999-12'},
            {BLARG.a},
        )
        yield (
            {'cardSearchFilter[dateCreated]': '1999-11'},
            set(),
        )
        yield (
            {'cardSearchFilter[dateCreated]': '2012-12-31'},
            {BLARG.b},
        )
        yield (
            {'cardSearchFilter[dateCreated][after]': '2030'},
            set(),
        )
        yield (
            {'cardSearchFilter[dateCreated][after]': '2011'},
            {BLARG.b, BLARG.c},
        )
        yield (
            {'cardSearchFilter[dateCreated][before]': '2012-12'},
            {BLARG.a},
        )
        yield (
            {'cardSearchText': 'bbbb'},
            {BLARG.b},
        )
        yield (
            {'cardSearchText': '-bbbb'},
            {BLARG.a, BLARG.c},
        )
        yield (
            {'cardSearchText': 'danger'},
            {BLARG.b, BLARG.c},
        )
        yield (
            {'cardSearchText': 'dangre'},
            {BLARG.b, BLARG.c},
        )
        yield (
            {'cardSearchText': '"dangre"'},
            set(),
        )
        yield (
            {'cardSearchText': 'danger -repulsive'},
            {BLARG.c},
        )
        yield (
            {'cardSearchText': '"nothing valued is here"'},
            {BLARG.a},
        )
        yield (
            {'cardSearchText': '"nothing valued here"'},
            set(),
        )
        yield (
            {'cardSearchText': '"what is here"'},
            {BLARG.b},
        )

    def cardsearch_integer_cases(self) -> Iterator[tuple[dict[str, str], set[str] | list[str]]]:
        # cases that depend on integer values getting indexed
        yield (
            {'sort[integer-value]': 'dcat:servesDataset.dcat:spatialResolutionInMeters'},
            [BLARG.b, BLARG.a, BLARG.c],  # ordered list
        )
        yield (
            {'sort[integer-value]': '-dcat:servesDataset.dcat:spatialResolutionInMeters'},
            [BLARG.c, BLARG.a, BLARG.b],  # ordered list
        )

    def valuesearch_simple_cases(self) -> Iterator[tuple[dict[str, str], set[str]]]:
        yield (
            {'valueSearchPropertyPath': 'references'},
            {BLARG.b, BLARG.c},
        )
        yield (
            {'valueSearchPropertyPath': 'dateCreated'},
            {'1999', '2012', '2024'},
        )
        # TODO: more

    def valuesearch_complex_cases(self) -> Iterator[tuple[dict[str, str], set[str]]]:
        yield (
            {
                'valueSearchPropertyPath': 'references',
                'valueSearchFilter[resourceType]': BLARG.Thing,
            },
            {BLARG.b, BLARG.c},
        )
        yield (
            {
                'valueSearchPropertyPath': 'references',
                'valueSearchText': 'bbbb',
            },
            {BLARG.b},
        )
        # TODO: more

    def _index_indexcards(self, indexcards: Iterable[trove_db.Indexcard]):
        _messages_chunk = messages.MessagesChunk(
            messages.MessageType.UPDATE_INDEXCARD,
            [_indexcard.id for _indexcard in indexcards],
        )
        self.assertTrue(all(
            _response.is_done
            for _response in self.index_strategy.pls_handle_messages_chunk(_messages_chunk)
        ))
        self.current_index.pls_refresh()

    def _create_indexcard(self, focus_iri: str, rdf_tripledict: rdf.RdfTripleDictionary) -> trove_db.Indexcard:
        _suid = factories.SourceUniqueIdentifierFactory()
        _raw = factories.RawDatumFactory(
            suid=_suid,
        )
        _indexcard = trove_db.Indexcard.objects.create(
            source_record_suid=_suid,
        )
        # an osfmap_json card is required for indexing, but not used in these tests
        trove_db.DerivedIndexcard.objects.create(
            upriver_indexcard=_indexcard,
            deriver_identifier=trove_db.ResourceIdentifier.objects.get_or_create_for_iri(TROVE['derive/osfmap_json']),
        )
        trove_db.LatestIndexcardRdf.objects.create(
            from_raw_datum=_raw,
            indexcard=_indexcard,
            focus_iri=focus_iri,
            rdf_as_turtle=rdf.turtle_from_tripledict(rdf_tripledict),
            turtle_checksum_iri='foo',  # not enforced
        )
        self._indexcard_focus_by_uuid[str(_indexcard.uuid)] = focus_iri
        return _indexcard

    def _create_supplement(
        self,
        indexcard: trove_db.Indexcard,
        focus_iri: str,
        rdf_tripledict: rdf.RdfTripleDictionary,
    ) -> trove_db.SupplementaryIndexcardRdf:
        _supp_suid = factories.SourceUniqueIdentifierFactory()
        _supp_raw = factories.RawDatumFactory(suid=_supp_suid)
        return trove_db.SupplementaryIndexcardRdf.objects.create(
            from_raw_datum=_supp_raw,
            indexcard=indexcard,
            supplementary_suid=_supp_suid,
            focus_iri=focus_iri,
            rdf_as_turtle=rdf.turtle_from_tripledict(rdf_tripledict),
            turtle_checksum_iri='sup',  # not enforced
        )