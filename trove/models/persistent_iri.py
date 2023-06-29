import dataclasses
import re

from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField
from django.db import models
import gather


# quoth <https://www.rfc-editor.org/rfc/rfc3987.html#section-2.2>:
#   scheme = ALPHA *( ALPHA / DIGIT / "+" / "-" / "." )
IRI_SCHEME_REGEX = re.compile(
    r'[a-z]'            # one letter from the english alphabet
    r'[a-z0-9+-.]*'     # zero or more letters, decimal numerals, or the symbols `+`, `-`, or `.`
)
COLON = ':'
SLASH_SLASH = '//'


# for choosing among multiple schemes
IRI_SCHEME_PREFERENCE_ORDER = (
    'https',
    'http',
)


@dataclasses.dataclass
class SchemeSplitIri:
    scheme: str
    iri_remainder: str
    has_authority: bool

    @classmethod
    def from_iri(cls, iri: str):
        (_scheme, _colon, _remainder) = iri.partition(COLON)
        if not IRI_SCHEME_REGEX.fullmatch(_scheme):
            raise ValueError(f'does not look like an iri (got "{iri}")')
        return cls(
            scheme=_scheme,
            iri_remainder=_remainder,
            has_authority=_remainder.startswith(SLASH_SLASH),
        )

    @property
    def scheme_if_authorityless(self) -> str:
        if self.has_authority:
            return ''
        return self.scheme


def validate_iri_scheme(iri_scheme):
    '''raise a django ValidationError if not a valid iri scheme
    '''
    if not isinstance(iri_scheme, str):
        raise ValidationError('not a string')
    if not IRI_SCHEME_REGEX.fullmatch(iri_scheme):
        raise ValidationError('not a valid iri scheme')


def validate_iri_scheme_or_empty(iri_scheme):
    '''raise a django ValidationError if not a valid iri scheme or empty string
    '''
    if '' != iri_scheme:  # empty string allowed
        validate_iri_scheme(iri_scheme)


class PersistentIriManager(models.Manager):
    def queryset_for_iri(self, iri: str):
        try:
            _split = SchemeSplitIri.from_iri(iri)
        except ValueError:
            return self.none()  # TODO: would it be better to raise?
        else:
            return self.filter(
                authorityless_scheme=_split.scheme_if_authorityless,
                schemeless_iri=_split.iri_remainder,
            )

    def get_for_iri(self, iri: str) -> 'PersistentIri':
        return self.queryset_for_iri(iri).get()  # may raise PersistentIri.DoesNotExist

    def get_or_create_for_iri(self, iri: str) -> 'PersistentIri':
        # may raise if invalid
        _split = SchemeSplitIri.from_iri(iri)
        (_piri, _created) = self.get_or_create(
            authorityless_scheme=_split.scheme_if_authorityless,
            schemeless_iri=_split.iri_remainder,
            defaults={
                'scheme_list': [_split.scheme],
            },
        )
        if _split.scheme not in _piri.scheme_list:
            _piri.scheme_list.append(_split.scheme)
            _piri.save()
        return _piri

    def save_equivalent_piris(
        self,
        tripledict: gather.RdfTripleDictionary,
        focus_iri: str,
    ) -> list['PersistentIri']:
        _piris = [self.get_or_create_for_iri(focus_iri)]
        _piris.extend(
            self.get_or_create_for_iri(_sameas_iri)
            for _sameas_iri in tripledict[focus_iri].get(gather.OWL.sameAs, ())
            if _sameas_iri != focus_iri
        )
        return _piris


# wild assertion:
#   if two IRIs differ only in their `scheme`
#   and have non-empty `authority` component,
#   they may safely be considered equivalent.
# (while this is not strictly true, it should be true enough
#  (and helps avoid hand-wringing about "http" vs "https" --
#   use either or both, it's fine))
class PersistentIri(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    # empty string if the IRI uses "://" (and therefore has an `authority` component)
    # otherwise the IRI `scheme` (which implicitly does not use IP or DNS for naming)
    authorityless_scheme = models.TextField(
        blank=True,
        validators=[validate_iri_scheme_or_empty],
    )
    # the remainder of the IRI after the scheme (not including the ":")
    schemeless_iri = models.TextField()
    # all schemes seen with this IRI, in the order they were seen
    # (not indexed or used for comparison; just for making iri string)
    scheme_list = ArrayField(
        models.TextField(validators=[validate_iri_scheme]),
    )

    objects = PersistentIriManager()

    class Meta:
        unique_together = [
            ('authorityless_scheme', 'schemeless_iri'),
        ]
        constraints = [
            models.CheckConstraint(
                name='has_at_least_one_scheme',
                check=models.Q(scheme_list__len__gt=0),
            ),
            models.CheckConstraint(
                name='authorityless_scheme__is_empty_or_known',
                check=(
                    models.Q(authorityless_scheme='')
                    | models.Q(scheme_list__contains=[models.F('authorityless_scheme')])
                ),
            ),
            models.CheckConstraint(name='has_authority_or_no_need_for_one', check=(
                # either the IRI has an authority (and we mostly ignore the scheme)
                models.Q(schemeless_iri__startswith=SLASH_SLASH, authorityless_scheme='')
                | (  # ...or the IRI has no authority (and the scheme is important)
                    ~models.Q(authorityless_scheme='')
                    & ~models.Q(schemeless_iri__startswith=SLASH_SLASH)
                )
            )),
        ]

    def __repr__(self):
        return ''.join((
            f'<{self.__class__.__qualname__}(',
            f'schemeless_iri="{self.schemeless_iri}",',
            f' scheme_list={self.scheme_list},',
            f' authorityless_scheme="{self.authorityless_scheme}")',
        ))

    __str__ = __repr__

    def build_iri(self) -> str:
        _scheme = (
            self.authorityless_scheme
            or self.choose_a_scheme()
        )
        return ''.join((_scheme, COLON, self.schemeless_iri))

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
        _split = SchemeSplitIri.from_iri(iri)
        return (
            self.schemeless_iri == _split.iri_remainder
            and self.authorityless_scheme == _split.scheme_if_authorityless
        )

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
