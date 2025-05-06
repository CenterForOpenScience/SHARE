import urllib

from django.test import SimpleTestCase

from trove.trovesearch.search_params import (
    SearchText,
    SearchFilter, DEFAULT_PROPERTYPATH_SET,
)
from trove.util.queryparams import QueryparamName, queryparams_from_querystring
from trove.vocab.namespaces import OSFMAP, RDF, DCTERMS


class TestSearchText(SimpleTestCase):
    def test_from_queryparam_family_with_empty_value(self):
        _qp = queryparams_from_querystring('myBlargText[foo]=')
        result = SearchText.from_queryparam_family(_qp, 'myBlargText')
        self.assertEqual(result, frozenset())

    def test_single_word(self):
        qp = queryparams_from_querystring('myBlargText=word')
        (st,) = SearchText.from_queryparam_family(qp, 'myBlargText')
        self.assertEqual(st.text, "word")
        self.assertEqual(st.propertypath_set, DEFAULT_PROPERTYPATH_SET)

    def test_multiple_words(self):
        qp = queryparams_from_querystring('myBlargText=apple&myBlargText=banana&myBlargText=cherry&anotherText=no')
        result = SearchText.from_queryparam_family(qp, 'myBlargText')
        self.assertEqual(result, {SearchText('apple'), SearchText('banana'), SearchText('cherry')})

    def test_text_with_spaces(self):
        phrases = [
            "multi word phrase",
            'phrase with "double quotes"',
            '~phrase~ with +special.characters AND \'mismatched quotes"'
        ]
        for phrase in phrases:
            qp = queryparams_from_querystring(urllib.parse.urlencode({'myBlargText': phrase}))
            (st,) = SearchText.from_queryparam_family(qp, 'myBlargText')
            self.assertEqual(st.text, phrase)
            self.assertEqual(st.propertypath_set, DEFAULT_PROPERTYPATH_SET)

    def test_custom_propertypath_set(self):
        qp = queryparams_from_querystring('myBlargText[title]=foo')
        result = SearchText.from_queryparam_family(qp, 'myBlargText')
        self.assertEqual(result, {
            SearchText('foo', frozenset({(DCTERMS.title,)}))
        })


class TestSearchFilterPath(SimpleTestCase):
    def test_from_param(self):
        _cases = {
            ('foo[resourceType]', 'Project'): SearchFilter(
                propertypath_set=frozenset([(RDF.type,)]),
                value_set=frozenset([OSFMAP.Project]),
                operator=SearchFilter.FilterOperator.ANY_OF,
            ),
            ('foo[urn:foo][none-of]', 'urn:bar,urn:baz'): SearchFilter(
                propertypath_set=frozenset([('urn:foo',)]),
                value_set=frozenset(['urn:bar', 'urn:baz']),
                operator=SearchFilter.FilterOperator.NONE_OF,
            ),
            ('foo[dateCreated]', '2000'): SearchFilter(
                propertypath_set=frozenset([(DCTERMS.created,)]),
                value_set=frozenset(['2000']),
                operator=SearchFilter.FilterOperator.AT_DATE,
            ),
            ('foo[dateCreated,dateModified][after]', '2000-01-01'): SearchFilter(
                propertypath_set=frozenset([
                    (DCTERMS.created,),
                    (DCTERMS.modified,),
                ]),
                value_set=frozenset(['2000-01-01']),
                operator=SearchFilter.FilterOperator.AFTER,
            ),
            ('foo[dateModified,isPartOf.dateModified][after]', '2000-01-01'): SearchFilter(
                propertypath_set=frozenset([
                    (DCTERMS.modified,),
                    (DCTERMS.isPartOf, DCTERMS.modified,),
                ]),
                value_set=frozenset(['2000-01-01']),
                operator=SearchFilter.FilterOperator.AFTER,
            ),
            ('foo[dateWithdrawn][before]', '2000-01-01'): SearchFilter(
                propertypath_set=frozenset([(OSFMAP.dateWithdrawn,)]),
                value_set=frozenset(['2000-01-01']),
                operator=SearchFilter.FilterOperator.BEFORE,
            ),
            ('foo[creator][is-present]', ''): SearchFilter(
                propertypath_set=frozenset([(DCTERMS.creator,)]),
                value_set=frozenset(),
                operator=SearchFilter.FilterOperator.IS_PRESENT,
            ),
            ('foo[creator.creator.creator][is-absent]', 'nothing'): SearchFilter(
                propertypath_set=frozenset([(DCTERMS.creator, DCTERMS.creator, DCTERMS.creator,)]),
                value_set=frozenset(),
                operator=SearchFilter.FilterOperator.IS_ABSENT,
            ),
            ('foo[creator,creator,creator][is-absent]', 'nothing'): SearchFilter(
                propertypath_set=frozenset([(DCTERMS.creator,)]),
                value_set=frozenset(),
                operator=SearchFilter.FilterOperator.IS_ABSENT,
            ),
            ('foo[affiliation,isPartOf.affiliation,isContainedBy.affiliation]', 'http://foo.example/'): SearchFilter(
                propertypath_set=frozenset([
                    (OSFMAP.isContainedBy, OSFMAP.affiliation,),
                    (DCTERMS.isPartOf, OSFMAP.affiliation,),
                    (OSFMAP.affiliation,),
                ]),
                value_set=frozenset(['http://foo.example/']),
                operator=SearchFilter.FilterOperator.ANY_OF,
            ),
        }
        for (_paramname, _paramvalue), _expectedfilter in _cases.items():
            _actualfilter = SearchFilter.from_filter_param(
                QueryparamName.from_str(_paramname),
                _paramvalue,
            )
            self.assertEqual(_expectedfilter, _actualfilter)
