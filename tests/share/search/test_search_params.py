from django.test import SimpleTestCase

from share.search.search_params import (
    Textsegment,
    SearchFilter,
)
from trove.util.queryparams import QueryparamName
from trove.vocab.namespaces import OSFMAP, RDF, DCTERMS


class TestTextsegment(SimpleTestCase):
    def test_empty(self):
        for _empty_input in ('', '""', '*', '-', '-""'):
            _empty = set(Textsegment.iter_from_text(_empty_input))
            self.assertFalse(_empty)

    def test_fuzz(self):
        _fuzzword = set(Textsegment.iter_from_text('woord'))
        self.assertEqual(_fuzzword, frozenset((
            Textsegment('woord', is_fuzzy=True, is_negated=False, is_openended=True),
        )))
        _fuzzphrase = set(Textsegment.iter_from_text('wibbleplop worble polp elbbiw'))
        self.assertEqual(_fuzzphrase, frozenset((
            Textsegment('wibbleplop worble polp elbbiw', is_fuzzy=True, is_negated=False, is_openended=True),
        )))

    def test_exact(self):
        _exactword = set(Textsegment.iter_from_text('"woord"'))
        self.assertEqual(_exactword, frozenset((
            Textsegment('woord', is_fuzzy=False, is_negated=False, is_openended=False),
        )))
        _exactphrase = set(Textsegment.iter_from_text('"wibbleplop worble polp elbbiw"'))
        self.assertEqual(_exactphrase, frozenset((
            Textsegment('wibbleplop worble polp elbbiw', is_fuzzy=False, is_negated=False, is_openended=False),
        )))
        _openphrase = set(Textsegment.iter_from_text('"wibbleplop worble polp elbbiw'))
        self.assertEqual(_openphrase, frozenset((
            Textsegment('wibbleplop worble polp elbbiw', is_fuzzy=False, is_negated=False, is_openended=True),
        )))

    def test_minus(self):
        _minusword = set(Textsegment.iter_from_text('-woord'))
        self.assertEqual(_minusword, frozenset((
            Textsegment('woord', is_fuzzy=False, is_negated=True, is_openended=False),
        )))
        _minusexactword = set(Textsegment.iter_from_text('-"woord droow"'))
        self.assertEqual(_minusexactword, frozenset((
            Textsegment('woord droow', is_fuzzy=False, is_negated=True, is_openended=False),
        )))
        _minustwo = set(Textsegment.iter_from_text('abc -def -g hi there'))
        self.assertEqual(_minustwo, frozenset((
            Textsegment('def', is_fuzzy=False, is_negated=True, is_openended=False),
            Textsegment('g', is_fuzzy=False, is_negated=True, is_openended=False),
            Textsegment('hi there', is_fuzzy=True, is_negated=False, is_openended=True),
            Textsegment('abc', is_fuzzy=True, is_negated=False, is_openended=False),
        )))

    def test_combo(self):
        _combo = set(Textsegment.iter_from_text('wibbleplop -"worble polp" elbbiw -but "exactly'))
        self.assertEqual(_combo, frozenset((
            Textsegment('worble polp', is_fuzzy=False, is_negated=True, is_openended=False),
            Textsegment('elbbiw', is_fuzzy=True, is_negated=False, is_openended=False),
            Textsegment('wibbleplop', is_fuzzy=True, is_negated=False, is_openended=False),
            Textsegment('but', is_fuzzy=False, is_negated=True, is_openended=False),
            Textsegment('exactly', is_fuzzy=False, is_negated=False, is_openended=True),
        )))


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
