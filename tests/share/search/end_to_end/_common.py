import datetime
import itertools
from urllib.parse import urlencode
from typing import Iterator

from primitive_metadata import primitive_rdf as rdf

from trove.vocab import mediatypes
from trove.vocab.namespaces import RDF, DCTERMS, OWL, FOAF, DCAT, BLARG, OSFMAP, TROVE
from tests.share.search.index_strategy._with_real_services import RealElasticTestCase
from tests.trove.factories import (
    create_indexcard,
    index_indexcards,
)


# abstract base class -- subclasses need to implement RealElasticTestCase.get_index_strategy
class End2EndSearchTestCase(RealElasticTestCase):
    MEDIATYPES = (mediatypes.JSONAPI,)  # TODO: more

    def setUp(self):
        super().setUp()
        _indexcards = self._create_test_cards()
        index_indexcards(self.index_strategy, _indexcards)

    ###
    # test methods

    def test_like_osfsearch(self):
        # cardsearch
        for _queryparams, _expected_focus_iris in self._cardsearch_cases():
            self._test_get_for_each_mediatype(
                url_path='/trove/index-card-search',
                queryparams=_queryparams,
                actual_getter=self._get_cardsearch_focus_iris,
                expected=_expected_focus_iris,
            )
        # valuesearch
        for _queryparams, _expected_values in self._valuesearch_cases():
            self._test_get_for_each_mediatype(
                url_path='/trove/index-value-search',
                queryparams=_queryparams,
                actual_getter=self._get_valuesearch_values,
                expected=_expected_values,
            )

    ###
    # internals

    def _test_get_for_each_mediatype(
        self,
        url_path,
        queryparams,
        actual_getter,
        expected,
    ):
        for _mediatype in self.MEDIATYPES:
            _response = self._send_get(url_path, queryparams, _mediatype)
            _actual = actual_getter(_response)
            self.assertEqual(_actual, expected)

    def _create_test_cards(self):
        self.all_card_focus_iris = {
            BLARG.myproj,
            BLARG.mypreprint,
        }
        self.card__myproj = create_indexcard(BLARG.myproj, {
            RDF.type: {OSFMAP.Project},
            DCTERMS.title: {rdf.literal('my project', language='en')},
            DCTERMS.description: {rdf.literal('this project sure is.', language='en')},
            OWL.sameAs: {'https://doi.example/13.618/7', 'http://raid.example/whatever'},
            DCTERMS.creator: {BLARG.a_person, BLARG.nother_person},
            OSFMAP.keyword: {rdf.literal('keyword', language='en')},
            DCAT.accessService: {BLARG.anOsfOrSomething},
            DCTERMS.created: {rdf.literal(datetime.date(2020, 2, 2))},
        }, rdf_tripledict={
            BLARG.a_person: {
                RDF.type: {DCTERMS.Agent, FOAF.Person},
                FOAF.name: {rdf.literal('peerrr sssssooo oooonnn nnnnnnnn')},
            },
            BLARG.nother_person: {
                RDF.type: {DCTERMS.Agent, FOAF.Person},
                FOAF.name: {rdf.literal('nootthhh eeerrrppp peeeerrrrssssooooonnnnn')},
                OSFMAP.affiliation: {BLARG.an_institution},
            },
            BLARG.an_institution: {
                RDF.type: {DCTERMS.Agent, FOAF.Organization},
                FOAF.name: {rdf.literal('innssttt iiitttuuuu ttttiiiioooonnnnn')},
                OSFMAP.affiliation: {BLARG.an_institution},
            },
        }, deriver_iris=(TROVE['derive/osfmap_json'],))
        self.card__mypreprint = create_indexcard(BLARG.mypreprint, {
            RDF.type: {OSFMAP.Preprint},
            DCTERMS.title: {rdf.literal('my preprint', language='en')},
            DCTERMS.description: {rdf.literal('this preprint sure is that.', language='en')},
            OWL.sameAs: {'https://doi.example/13.618/11', 'http://raid.example/whateverz'},
            DCTERMS.creator: {BLARG.nother_person, BLARG.third_person},
            OSFMAP.keyword: {
                rdf.literal('keyword', language='en'),
                rdf.literal('lockword', language='en'),
            },
            DCAT.accessService: {BLARG.anOsfOrSomething},
            DCTERMS.created: {rdf.literal(datetime.date(2022, 2, 2))},
        }, rdf_tripledict={
            BLARG.nother_person: {
                RDF.type: {DCTERMS.Agent, FOAF.Person},
                FOAF.name: {rdf.literal('nootthhh eeerrrppp peeeerrrrssssooooonnnnn')},
            },
            BLARG.third_person: {
                RDF.type: {DCTERMS.Agent, FOAF.Person},
                FOAF.name: {rdf.literal('⚞33️⃣🕒🥉 ☘️🎶 ³⑶➂ ⚞👩‍👩‍👧⚟ ㍛⬱⚟')},
            },
            BLARG.an_institution: {
                RDF.type: {DCTERMS.Agent, FOAF.Organization},
                FOAF.name: {rdf.literal('innssttt iiitttuuuu ttttiiiioooonnnnn')},
            },
        }, deriver_iris=(TROVE['derive/osfmap_json'],))
        return [
            self.card__myproj,
            self.card__mypreprint,
        ]

    def _send_get(self, base_url, queryparams, mediatype):
        assert '?' not in base_url
        queryparams['acceptMediatype'] = mediatype
        _url = f'{base_url}?{urlencode(queryparams)}'
        return self.client.get(_url)

    def _get_cardsearch_focus_iris(self, response):
        if response.headers['Content-Type'] != mediatypes.JSONAPI:
            raise NotImplementedError('TODO: more mediatypes')
        _response_json = response.json()
        return set(itertools.chain.from_iterable(
            _json_resource['attributes']['resourceIdentifier']
            for _json_resource in _response_json['included']
            if _json_resource['type'] == 'index-card'
        ))

    def _get_valuesearch_values(self, response):
        if response.headers['Content-Type'] != mediatypes.JSONAPI:
            raise NotImplementedError('TODO: more mediatypes')
        _response_json = response.json()
        return set(itertools.chain.from_iterable(
            _json_resource['attributes']['resourceIdentifier']
            for _json_resource in _response_json['included']
            if _json_resource['type'] == 'index-card'
        ))

    def _cardsearch_cases(self) -> Iterator[tuple[dict[str, str], set[str] | list[str]]]:
        yield (  # empty baseline
            {},  # no query params
            self.all_card_focus_iris,
        )
        yield (  # osf-search "all types" tab
            {
                'cardSearchFilter[resourceType]': 'Registration,RegistrationComponent,Project,ProjectComponent,Preprint,Agent,File',
                'cardSearchFilter[accessService]': BLARG.anOsfOrSomething,
                'cardSearchText[*,creator.name,isContainedBy.creator.name]': '',
                'sort': '-relevance',
            },
            self.all_card_focus_iris,
        )
        yield (  # osf-search "all types" tab (with cardSearchText)
            {
                'cardSearchFilter[resourceType]': 'Registration,RegistrationComponent,Project,ProjectComponent,Preprint,Agent,File',
                'cardSearchFilter[accessService]': BLARG.anOsfOrSomething,
                'cardSearchText[*,creator.name,isContainedBy.creator.name]': '⚞👩‍👩‍👧⚟',
                'sort': '-relevance',
            },
            {BLARG.mypreprint},
        )
        yield (  # osf-search "projects" tab
            {
                'cardSearchFilter[resourceType]': 'Project,ProjectComponent',
                'cardSearchFilter[accessService]': BLARG.anOsfOrSomething,
                'cardSearchText[*,creator.name,isContainedBy.creator.name]': '',
                'sort': '-relevance',
            },
            {BLARG.myproj},
        )
        yield (  # osf-search "preprints" tab
            {
                'cardSearchFilter[resourceType]': 'Preprint',
                'cardSearchFilter[accessService]': BLARG.anOsfOrSomething,
                'cardSearchText[*,creator.name,isContainedBy.creator.name]': '',
                'sort': '-relevance',
            },
            {BLARG.mypreprint},
        )
        yield (  # osf-search "registrations" tab
            {
                'cardSearchFilter[resourceType]': 'Registration,RegistrationComponent',
                'cardSearchFilter[accessService]': BLARG.anOsfOrSomething,
                'cardSearchText[*,creator.name,isContainedBy.creator.name]': '',
                'sort': '-relevance',
            },
            set(),  # TODO
        )
        yield (  # osf-search "files" tab
            {
                'cardSearchFilter[resourceType]': 'File',
                'cardSearchFilter[accessService]': BLARG.anOsfOrSomething,
                'cardSearchText[*,creator.name,isContainedBy.creator.name]': '',
                'sort': '-relevance',
            },
            set(),  # TODO
        )

    def _valuesearch_cases(self) -> Iterator[tuple[dict[str, str], set[str] | list[str]]]:
        yield (  # simple baseline
            {'valueSearchPropertyPath': 'resourceType'},
            {OSFMAP.Project, OSFMAP.Preprint},
        )
        yield (  # osf-search "all types" tab; "creator" facet
            {
                'valueSearchPropertyPath': 'creator',
                'cardSearchFilter[resourceType]': 'Registration,RegistrationComponent,Project,ProjectComponent,Preprint,Agent,File',
                'cardSearchFilter[accessService]': BLARG.anOsfOrSomething,
                'cardSearchText[*,creator.name,isContainedBy.creator.name]': '',
                'sort': '-relevance',
            },
            {BLARG.a_person, BLARG.nother_person, BLARG.third_person},
        )
        yield (  # osf-search "all types" tab; "creator" facet with valueSearchText
            {
                'valueSearchPropertyPath': 'creator',
                'valueSearchText': '⚞👩‍👩‍👧⚟',
                'cardSearchFilter[resourceType]': 'Registration,RegistrationComponent,Project,ProjectComponent,Preprint,Agent,File',
                'cardSearchFilter[accessService]': BLARG.anOsfOrSomething,
                'cardSearchText[*,creator.name,isContainedBy.creator.name]': '',
                'sort': '-relevance',
            },
            {BLARG.third_person},
        )
        yield (  # osf-search "preprints" tab; "creator" facet
            {
                'valueSearchPropertyPath': 'creator',
                'cardSearchFilter[resourceType]': 'Preprint',
                'cardSearchFilter[accessService]': BLARG.anOsfOrSomething,
                'cardSearchText[*,creator.name,isContainedBy.creator.name]': '',
                'sort': '-relevance',
            },
            {BLARG.nother_person, BLARG.third_person},
        )
        yield (  # osf-search "all types" tab; "dateCreated" facet
            {
                'valueSearchPropertyPath': 'dateCreated',
                'cardSearchFilter[resourceType]': 'Registration,RegistrationComponent,Project,ProjectComponent,Preprint,Agent,File',
                'cardSearchFilter[accessService]': BLARG.anOsfOrSomething,
                'cardSearchText[*,creator.name,isContainedBy.creator.name]': '',
                'sort': '-relevance',
            },
            {'2020', '2022'},  # year histogram
        )
