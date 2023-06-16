import re
import typing

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

IRI_SCHEME_PREFERENCE_ORDER = (
    'https',
    'http',
)

COLON = ':'
COLON_SLASH_SLASH = '://'


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


def validate_schemeless_iri(schemeless_iri):
    '''raise a django ValidationError if not (enough like) a valid iri without its scheme
    '''
    # quoth <https://www.rfc-editor.org/rfc/rfc3987.html#section-2.2>:
    #   IRI = scheme ":" ihier-part [ "?" iquery ] [ "#" ifragment ]
    # here, a "schemeless IRI" is everything after (and including) that ":"
    if not isinstance(schemeless_iri, str):
        raise ValidationError('not a string')
    if not schemeless_iri.startswith(COLON):
        raise ValidationError('does not start with ":"')
    # (as far as this validator cares, starting with  ":" is enough)


class PersistentIriManager(models.Manager):
    def get_from_str(self, iri: str) -> 'PersistentIri':
        try:
            (_, _authorityless_scheme, _schemeless_iri) = self._split_iri(iri)
        except ValueError:
            raise self.model.DoesNotExist
        return self.get(
            authorityless_scheme=_authorityless_scheme,
            schemeless_iri=_schemeless_iri,
        )

    def save_from_str(self, iri: str) -> 'PersistentIri':
        # may raise if invalid
        (_scheme, _authorityless_scheme, _schemeless_iri) = self._split_iri(iri)
        (_piri, _created) = self.get_or_create(
            authorityless_scheme=_authorityless_scheme,
            schemeless_iri=_schemeless_iri,
            defaults={
                'seen_scheme_set': [_scheme],
            },
        )
        if _created:
            assert _scheme in _piri.seen_scheme_set, 'but there\'s a check constraint!'
        elif _scheme not in _piri.seen_scheme_set:
            _piri.seen_scheme_set.append(_scheme)
            _piri.save()
        return _piri

    def save_multiple_from_str(self, iris: typing.Iterable[str]) -> list['PersistentIri']:
        _piris = []
        for _iri in iris:
            _piris.append(self.save_from_str(_iri))
        return _piris

    def save_equivalent_piris(
        self,
        tripledict: gather.RdfTripleDictionary,
        focus_iri: str,
    ) -> list['PersistentIri']:
        _piris = [
            self.save_from_str(focus_iri),
        ]
        for _sameas_iri in tripledict[focus_iri].get(gather.OWL.sameAs, ()):
            _piris.append(self.save_from_str(_sameas_iri))
        return _piris

    def _split_iri(self, iri: str):
        _scheme_match = IRI_SCHEME_REGEX.match(iri)
        if not _scheme_match:
            raise ValueError(f'does not look like an iri (got "{iri}")')
        _scheme = _scheme_match.group()
        _schemeless_iri = iri[_scheme_match.end():]
        _authorityless_scheme = (
            ''
            if _schemeless_iri.startswith(COLON_SLASH_SLASH)
            else _scheme
        )
        return (_scheme, _authorityless_scheme, _schemeless_iri)


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

    # empty string if the IRI has an `authority` component, otherwise the IRI `scheme`
    authorityless_scheme = models.TextField(
        blank=True,
        validators=[validate_iri_scheme_or_empty],
    )
    # the remainder of the IRI after the scheme, including the initial ":"
    schemeless_iri = models.TextField(validators=[validate_schemeless_iri])

    # all schemes seen with this IRI -- not indexed or used for comparison
    seen_scheme_set = ArrayField(
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
                check=models.Q(iri_scheme_set__len__gt=0),
            ),
            models.CheckConstraint(
                name='authorityless_scheme__is_empty_or_known',
                check=(
                    models.Q(authorityless_scheme='')
                    | models.Q(iri_scheme_set__contains=models.F('authorityless_scheme'))
                ),
            ),
            models.CheckConstraint(name='has_authority_or_no_need_for_one', check=(
                # either the IRI has an authority (and we mostly ignore the scheme)
                models.Q(schemeless_iri__startswith=COLON_SLASH_SLASH, authorityless_scheme='')
                | (  # ...or the IRI has no authority (and the scheme is important)
                    ~models.Q(authorityless_scheme='')
                    & models.Q(schemeless_iri__startswith=COLON)
                    & ~models.Q(schemeless_iri__startswith=COLON_SLASH_SLASH)
                )
            )),
        ]

    def as_str(self) -> str:
        _scheme = (
            self.authorityless_scheme
            or self.choose_a_scheme()
        )
        return ''.join((_scheme, self.schemeless_iri))

    def choose_a_scheme(self) -> str:
        try:
            (_scheme,) = self.seen_scheme_set
        except ValueError:
            assert len(self.seen_scheme_set) > 0, 'but there\'s a check constraint!'
            try:
                _scheme = next(
                    _preferred_scheme
                    for _preferred_scheme in IRI_SCHEME_PREFERENCE_ORDER
                    if _preferred_scheme in self.seen_scheme_set
                )
            except StopIteration:  # strange case: no preference
                _scheme = self.seen_scheme_set[0]
        return _scheme

    def equivalent_to(self, iri: str):
        _scheme, _colon, _schemeless_iri = iri.partition(COLON)
        return (
            _colon == COLON
            and _schemeless_iri == self.schemeless_iri
            and self.authorityless_scheme in (_scheme, '')
        )

    def find_equivalent_iri(self, tripledict: gather.RdfTripleDictionary) -> str:
        _piri_as_str = self.as_str()
        if _piri_as_str in tripledict:
            return _piri_as_str
        for _iri, _twopledict in tripledict.items():
            _sameas_set = _twopledict.get(gather.OWL.sameAs, set())
            _is_equivalent = (
                self.equivalent_to(_iri)
                or _piri_as_str in _sameas_set
                or any(
                    self.equivalent_to(_sameas_iri)
                    for _sameas_iri in _sameas_set
                )
            )
            if _is_equivalent:
                return _iri
        raise ValueError(f'could not find "{_piri_as_str}" or equivalent')
