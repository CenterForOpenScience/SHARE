from django.test import SimpleTestCase

from trove.trovesearch.search_params import (
    SearchText,
    SearchFilter, DEFAULT_PROPERTYPATH_SET,
)
from trove.util.queryparams import QueryparamName
from trove.vocab.namespaces import OSFMAP, RDF, DCTERMS


from django.test import SimpleTestCase
from trove.trovesearch.search_params import SearchText

class TestSearchText(SimpleTestCase):
    def test_empty_text_list(self):
        inputs = []
        results = [SearchText(text) for text in inputs]
        self.assertEqual(results, [])

    def test_single_word(self):
        st = SearchText("word")
        self.assertEqual(st.text, "word")
        self.assertEqual(st.propertypath_set, DEFAULT_PROPERTYPATH_SET)

    def test_multiple_words(self):
        words = ["apple", "banana", "cherry"]
        results = [SearchText(word) for word in words]
        self.assertEqual(len(results), 3)
        self.assertIn(SearchText("banana"), results)

    def test_text_with_spaces(self):
        phrase = "multi word phrase"
        st = SearchText(phrase)
        self.assertEqual(st.text, phrase)
        self.assertEqual(st.propertypath_set, DEFAULT_PROPERTYPATH_SET)

    def test_custom_propertypath_set(self):
        custom_set = frozenset(["some:path"])
        st = SearchText("hello", propertypath_set=custom_set)
        self.assertEqual(st.propertypath_set, custom_set)

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
