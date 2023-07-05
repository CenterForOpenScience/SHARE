import re
import typing

from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.functions import Substr, StrIndex
import gather


# quoth <https://www.rfc-editor.org/rfc/rfc3987.html#section-2.2>:
#   scheme = ALPHA *( ALPHA / DIGIT / "+" / "-" / "." )
IRI_SCHEME_REGEX = re.compile(
    r'[a-z]'            # one letter from the english alphabet
    r'[a-z0-9+-.]*'     # zero or more letters, decimal numerals, or the symbols `+`, `-`, or `.`
)
IRI_SCHEME_REGEX_IGNORECASE = re.compile(IRI_SCHEME_REGEX.pattern, flags=re.IGNORECASE)
COLON = ':'
COLON_SLASH_SLASH = '://'


# for choosing among multiple schemes
IRI_SCHEME_PREFERENCE_ORDER = (
    'https',
    'http',
)


def get_sufficiently_unique_iri_and_scheme(iri: str) -> tuple[str, str]:
    _scheme_match = IRI_SCHEME_REGEX_IGNORECASE.match(iri)
    if not _scheme_match:
        raise ValueError(f'does not look like an iri (got "{iri}")')
    _scheme = _scheme_match.group().lower()
    _remainder = iri[_scheme_match.end():]
    if _remainder.startswith(COLON_SLASH_SLASH):
        return (_remainder, _scheme)
    return (iri, _scheme)


def validate_iri_scheme(iri_scheme):
    '''raise a django ValidationError if not a valid iri scheme
    '''
    if not isinstance(iri_scheme, str):
        raise ValidationError('not a string')
    if not IRI_SCHEME_REGEX.fullmatch(iri_scheme):
        raise ValidationError('not a valid iri scheme')


def validate_sufficiently_unique_iri(suffuniq_iri: str):
    '''raise a django ValidationError if not a valid "sufficiently unique iri"

     based on a wild assertion:
       if two IRIs differ only in their `scheme`
       and have non-empty `authority` component,
       they may safely be considered equivalent.
     (while this is not strictly true, it should be true enough and helps avoid
     hand-wringing about "http" vs "https" -- use either or both, it's fine)
    '''
    if not isinstance(suffuniq_iri, str):
        raise ValidationError('not a string')
    (_maybescheme, _colonslashslash, _remainder) = suffuniq_iri.partition(COLON_SLASH_SLASH)
    if _colonslashslash:
        if _maybescheme:
            raise ValidationError('iri containing "://" should start with it')
    else:
        (_scheme, _colon, _remainder) = suffuniq_iri.partition(COLON)
        if not _colon:
            raise ValidationError('an iri needs a colon')
        validate_iri_scheme(_scheme)
    if not _remainder:
        raise ValidationError('need more iri beyond a scheme')


class PersistentIriManager(models.Manager):
    def queryset_for_iri(self, iri: str):
        return self.queryset_for_iris((iri,))

    def queryset_for_iris(self, iris: typing.Iterable[str]):
        # may raise if invalid
        _suffuniq_iris = set()
        for _iri in iris:
            (_suffuniq_iri, _) = get_sufficiently_unique_iri_and_scheme(_iri)
            _suffuniq_iris.add(_suffuniq_iri)
        return self.filter(sufficiently_unique_iri__in=_suffuniq_iris)

    def get_for_iri(self, iri: str) -> 'PersistentIri':
        return self.queryset_for_iri(iri).get()  # may raise PersistentIri.DoesNotExist

    def get_or_create_for_iri(self, iri: str) -> 'PersistentIri':
        # may raise if invalid
        (_suffuniq_iri, _scheme) = get_sufficiently_unique_iri_and_scheme(iri)
        (_piri, _created) = self.get_or_create(
            sufficiently_unique_iri=_suffuniq_iri,
            defaults={'scheme_list': [_scheme]},
        )
        if _scheme not in _piri.scheme_list:
            _piri.scheme_list.append(_scheme)
            _piri.save()
        return _piri

    def save_equivalent_piri_set(
        self,
        tripledict: gather.RdfTripleDictionary,
        focus_iri: str,
    ) -> list['PersistentIri']:
        _piri_set = [self.get_or_create_for_iri(focus_iri)]
        _piri_set.extend(
            self.get_or_create_for_iri(_sameas_iri)
            for _sameas_iri in tripledict[focus_iri].get(gather.OWL.sameAs, ())
            if _sameas_iri != focus_iri
        )
        return _piri_set


class PersistentIri(models.Model):
    objects = PersistentIriManager()

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    # if the IRI has "://" after its `scheme` (and therefore has an `authority` defined
    # using IP or DNS or similar), the substring starting with "://" is "unique enough"
    # -- otherwise, use the full IRI
    sufficiently_unique_iri = models.TextField(
        unique=True,
        validators=[validate_sufficiently_unique_iri],
    )
    # all schemes seen with this IRI, in the order they were seen
    # (not indexed or used for comparison; just for making iri string)
    scheme_list = ArrayField(
        models.TextField(validators=[validate_iri_scheme]),
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                name='%(app_label)s_%(class)s_suffuniq_iri_matches_scheme_list',
                check=(
                    # sufficiently_unique_iri contains ":" (to avoid Substr breaking)...
                    models.Q(sufficiently_unique_iri__contains=COLON)
                    & (  # ...and either...
                        models.Q(  # ...starts with "://" (with non-empty scheme_list)...
                            sufficiently_unique_iri__startswith=COLON_SLASH_SLASH,
                            scheme_list__len__gt=0,
                        )
                        | models.Q(  # ...or starts with the only item in scheme_list.
                            scheme_list=[Substr(
                                'sufficiently_unique_iri',
                                1,  # start of string (1-indexed)
                                StrIndex('sufficiently_unique_iri', models.Value(COLON)) - 1,
                            )],
                        )
                    )
                ),
            ),
        ]

    def __repr__(self):
        return (
            f'<{self.__class__.__qualname__}("{self.sufficiently_unique_iri}",'
            f' scheme_list={self.scheme_list}, id={self.id})'
        )

    __str__ = __repr__

    def build_iri(self) -> str:
        _suffuniq_iri = self.sufficiently_unique_iri
        return (
            ''.join((self.choose_a_scheme(), _suffuniq_iri))
            if _suffuniq_iri.startswith(COLON_SLASH_SLASH)
            else _suffuniq_iri
        )

    def choose_a_scheme(self) -> str:
        try:
            (_scheme,) = self.scheme_list
        except ValueError:
            assert len(self.scheme_list) > 0, 'but there\'s a check constraint!'
            try:
                _scheme = next(
                    _preferred_scheme
                    for _preferred_scheme in IRI_SCHEME_PREFERENCE_ORDER
                    if _preferred_scheme in self.scheme_list
                )
            except StopIteration:  # no preference
                # scheme_list is ordered; use the scheme seen first
                _scheme = self.scheme_list[0]
        return _scheme

    def equivalent_to_iri(self, iri: str):
        (_suffuniq_iri, _) = get_sufficiently_unique_iri_and_scheme(iri)
        return (self.sufficiently_unique_iri == _suffuniq_iri)

    def find_equivalent_iri(self, tripledict: gather.RdfTripleDictionary) -> str:
        _piri_iri = self.build_iri()
        if _piri_iri in tripledict:
            return _piri_iri
        for _iri, _twopledict in tripledict.items():
            _sameas_set = _twopledict.get(gather.OWL.sameAs, set())
            _is_equivalent = (
                _piri_iri in _sameas_set
                or self.equivalent_to_iri(_iri)
                or any(
                    self.equivalent_to_iri(_sameas_iri)
                    for _sameas_iri in _sameas_set
                )
            )
            if _is_equivalent:
                return _iri
        raise ValueError(f'could not find "{_piri_iri}" or equivalent in {set(tripledict.keys())}')
