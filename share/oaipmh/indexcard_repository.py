import uuid

import dateutil
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import OuterRef, Subquery

from share.oaipmh import errors as oai_errors
from share.oaipmh.verbs import OAIVerb
from share.oaipmh.response_renderer import OAIRenderer
from share.oaipmh.util import format_datetime
from share import models as share_db
from trove import models as trove_db
from trove.vocab.namespaces import OAI_DC


class OaiPmhRepository:
    NAME = 'Share/trove'
    REPOSITORY_IDENTIFIER = 'share.osf.io'
    IDENTIFER_DELIMITER = ':'
    GRANULARITY = 'YYYY-MM-DD'
    ADMIN_EMAILS = ['share-support@osf.io']

    # TODO better way of structuring this than a bunch of dictionaries?
    # this dictionary's keys are `metadataPrefix` values
    FORMATS = {
        'oai_dc': {
            'formatter_key': 'oai_dc',
            'deriver_iri': str(OAI_DC),
            'schema': 'http://www.openarchives.org/OAI/2.0/oai_dc.xsd',
            'namespace': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
        },
    }
    PAGE_SIZE = 13

    def handle_request(self, request, kwargs):
        xml = None
        renderer = OAIRenderer(self, request)
        verb, self.errors = OAIVerb.validate(**kwargs)

        if not self.errors:
            # No repeated arguments at this point
            kwargs = {k: v[0] for k, v in kwargs.items()}
            self.validate_metadata_prefix(kwargs.get('metadataPrefix'))

        if not self.errors:
            renderer.kwargs = kwargs
            handler_method = {
                'Identify': self._do_identify,
                'ListMetadataFormats': self._do_listmetadataformats,
                'ListSets': self._do_listsets,
                'ListIdentifiers': self._do_listidentifiers,
                'ListRecords': self._do_listrecords,
                'GetRecord': self._do_getrecord,

            }[verb.name]
            xml = handler_method(kwargs, renderer)

        return xml if not self.errors else renderer.errors(self.errors)

    def validate_metadata_prefix(self, maybe_prefix):
        if (
            maybe_prefix is not None
            and maybe_prefix not in self.FORMATS
        ):
            self.errors.append(oai_errors.BadFormat(maybe_prefix))

    def resolve_oai_identifier(self, identifier) -> trove_db.Indexcard:
        splid = identifier.split(self.IDENTIFER_DELIMITER)
        if len(splid) != 3 or splid[:2] != ['oai', self.REPOSITORY_IDENTIFIER]:
            self.errors.append(oai_errors.BadRecordID(identifier))
            return None
        try:
            return trove_db.Indexcard.objects.get(uuid=splid[-1])
        except (trove_db.Indexcard.DoesNotExist, DjangoValidationError):
            self.errors.append(oai_errors.BadRecordID(identifier))
            return None

    def sample_identifier(self):
        return self.oai_identifier(
            trove_db.Indexcard.objects
            .filter(deleted__isnull=True)
            .first()
        )

    def oai_identifier(self, indexcard):
        _uuid = (
            uuid.uuid4()
            if indexcard is None
            else indexcard.uuid
        )
        return self.IDENTIFER_DELIMITER.join((
            'oai',
            self.REPOSITORY_IDENTIFIER,
            str(_uuid),
        ))

    def _do_identify(self, kwargs, renderer):
        _earliest_date = (
            trove_db.LatestIndexcardRdf.objects
            .order_by('modified')
            .values_list('modified', flat=True)
            .first()
        )
        return renderer.identify(_earliest_date)

    def _do_listmetadataformats(self, kwargs, renderer):
        _formats = self.FORMATS
        if 'identifier' in kwargs:
            _indexcard = self.resolve_oai_identifier(kwargs['identifier'])
            _deriver_iris = set()
            _deriver_iri_lists = (
                trove_db.DerivedIndexcard.objects
                .filter(upriver_indexcard=_indexcard)
                .values_list('deriver_identifier__raw_iri_list', flat=True)
            )
            for _iri_list in _deriver_iri_lists:
                _deriver_iris.update(_iri_list)
            _formats = {
                prefix: format_info
                for prefix, format_info in self.FORMATS.items()
                if format_info['deriver_iri'] in _deriver_iris
            }
        return renderer.listMetadataFormats(_formats)

    def _do_listsets(self, kwargs, renderer):
        if 'resumptionToken' in kwargs:
            self.errors.append(oai_errors.BadResumptionToken(kwargs['resumptionToken']))
            return
        return renderer.listSets(
            share_db.Source.objects
            .exclude(is_deleted=True)
            .values_list('name', 'long_title')
        )

    def _do_listidentifiers(self, kwargs, renderer):
        _indexcards, _next_token = self._load_page(kwargs, just_identifiers=True)
        if self.errors:
            return
        return renderer.listIdentifiers(_indexcards, _next_token)

    def _do_listrecords(self, kwargs, renderer):
        _indexcards, _next_token = self._load_page(kwargs, just_identifiers=False)
        if self.errors:
            return
        return renderer.listRecords(_indexcards, _next_token)

    def _do_getrecord(self, kwargs, renderer):
        _indexcard = self.resolve_oai_identifier(kwargs['identifier'])
        if self.errors:
            return
        _oai_metadata = (
            _indexcard.derived_indexcard_set
            .filter(deriver_identifier__in=self._deriver_identifier_queryset(kwargs))
            .values_list('derived_text', flat=True)
            .first()
        )
        _oai_datestamp = (
            trove_db.LatestIndexcardRdf.objects
            .filter(indexcard=_indexcard)
            .values_list('modified', flat=True)
            .first()
        )
        if _oai_metadata is None or _oai_datestamp is None:
            self.errors.append(oai_errors.BadFormatForRecord(kwargs['metadataPrefix']))
        if self.errors:
            return
        # manual annotation (matching _load_page)
        _indexcard.oai_metadata = _oai_metadata
        _indexcard.oai_datestamp = _oai_datestamp
        return renderer.getRecord(_indexcard)

    def _load_page(self, kwargs, just_identifiers):
        if 'resumptionToken' in kwargs:
            try:
                _indexcard_queryset, kwargs = self._resume(kwargs['resumptionToken'])
            except (ValueError, KeyError):
                self.errors.append(oai_errors.BadResumptionToken(kwargs['resumptionToken']))
        else:
            _indexcard_queryset = self._get_indexcard_queryset(kwargs)
        if self.errors:
            return [], None
        _indexcard_queryset = _indexcard_queryset.annotate(
            oai_datestamp=Subquery(
                trove_db.LatestIndexcardRdf.objects
                .filter(indexcard_id=OuterRef('id'))
                .values_list('modified', flat=True)
                [:1]
            ),
        )
        if not just_identifiers:
            _indexcard_queryset = _indexcard_queryset.annotate(
                oai_metadata=Subquery(
                    trove_db.DerivedIndexcard.objects
                    .filter(
                        upriver_indexcard_id=OuterRef('id'),
                        deriver_identifier__in=self._deriver_identifier_queryset(kwargs),
                    )
                    .values_list('derived_text', flat=True)
                    [:1]
                ),
            )
        _indexcards = list(_indexcard_queryset)
        if not len(_indexcards):
            self.errors.append(oai_errors.NoResults())
            return [], None
        if len(_indexcards) <= self.PAGE_SIZE:
            _next_token = None  # Last page
        else:
            _indexcards = _indexcards[:self.PAGE_SIZE]
            _next_token = self._get_resumption_token(kwargs, last_id=_indexcards[-1].id)
        return _indexcards, _next_token

    def _get_indexcard_queryset(self, kwargs, catch=True, last_id=None):
        _indexcard_queryset = (
            trove_db.Indexcard.objects
            .filter(deleted__isnull=True)
            .filter(derived_indexcard_set__deriver_identifier__in=self._deriver_identifier_queryset(kwargs))
        )
        if 'from' in kwargs:
            try:
                _from = dateutil.parser.parse(kwargs['from'])
                _indexcard_queryset = _indexcard_queryset.filter(
                    trove_latestindexcardrdf_set__modified__gte=_from,
                )
            except ValueError:
                if not catch:
                    raise
                self.errors.append(oai_errors.BadArgument('Invalid value for', 'from'))
        if 'until' in kwargs:
            try:
                _until = dateutil.parser.parse(kwargs['until'])
                _indexcard_queryset = _indexcard_queryset.filter(
                    trove_latestindexcardrdf_set__modified__lte=_until,
                )
            except ValueError:
                if not catch:
                    raise
                self.errors.append(oai_errors.BadArgument('Invalid value for', 'until'))
        if 'set' in kwargs:
            _source_ids = (
                share_db.Source.objects
                .filter(name=kwargs['set'])
                .values_list('id', flat=True)
            )
            _indexcard_queryset = _indexcard_queryset.filter(
                source_record_suid__source_config__source_id__in=_source_ids,
            )
        if last_id is not None:
            _indexcard_queryset = _indexcard_queryset.filter(id__gt=last_id)
        _indexcard_queryset = (
            _indexcard_queryset
            .select_related('source_record_suid__source_config__source')
            .order_by('id')
        )
        if self.errors:
            return None
        # include one extra so we can tell whether this is the last page
        return _indexcard_queryset[:self.PAGE_SIZE + 1]

    def _resume(self, token):
        _from, _until, _set_spec, _prefix, _last_id = token.split('|')
        _kwargs = {}
        if _from:
            _kwargs['from'] = _from
        if _until:
            _kwargs['until'] = _until
        if _set_spec:
            _kwargs['set'] = _set_spec
        _kwargs['metadataPrefix'] = _prefix
        _indexcard_queryset = self._get_indexcard_queryset(
            _kwargs,
            catch=False,
            last_id=int(_last_id),
        )
        return _indexcard_queryset, _kwargs

    def _get_resumption_token(self, kwargs, last_id):
        _from = None
        _until = None
        if 'from' in kwargs:
            try:
                _from = dateutil.parser.parse(kwargs['from'])
            except ValueError:
                self.errors.append(oai_errors.BadArgument('Invalid value for', 'from'))
        if 'until' in kwargs:
            try:
                _until = dateutil.parser.parse(kwargs['until'])
            except ValueError:
                self.errors.append(oai_errors.BadArgument('Invalid value for', 'until'))
        _set_spec = kwargs.get('set', '')
        return self._format_resumption_token(_from, _until, _set_spec, kwargs['metadataPrefix'], last_id)

    def _format_resumption_token(self, from_, until, set_spec, prefix, last_id):
        # TODO something more opaque, maybe
        return '{}|{}|{}|{}|{}'.format(format_datetime(from_) if from_ else '', format_datetime(until) if until else '', set_spec, prefix, last_id)

    def _deriver_identifier_queryset(self, kwargs):
        return (
            trove_db.ResourceIdentifier.objects
            .queryset_for_iri(self.FORMATS[kwargs['metadataPrefix']]['deriver_iri'])
        )
