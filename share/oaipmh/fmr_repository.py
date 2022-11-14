import abc
import dateutil
import typing

from django.core.exceptions import ObjectDoesNotExist
from rdflib import URIRef

from share.models import FormattedMetadataRecord, Source, SourceUniqueIdentifier
from share.oaipmh import errors as oai_errors
from share.oaipmh.verbs import OAIVerb
from share.oaipmh.response_renderer import OAIRenderer
from share.oaipmh.util import format_datetime
from share.util import IDObfuscator, InvalidID


class RecordRepository(abc.ABC):
    def identify(self):
        return {
            # TODO: uriref keys, shacl:validation-report as feedback to implementors of this abc.ABC
            '@id': self.REPOSITORY_URI,
        }

    @abc.abstractmethod
    def list_formats(self, pid: URIRef = None) -> typing.Iterable[URIRef]:
        raise NotImplementedError('should yield identifiers of known/available record formats')

    # @abc.abstractmethod
    # def list_namespaces(self, pid=None) -> typing.Iterable[URIRef]:
    #     raise NotImplementedError('should yield identifiers of known/available metadata namespaces')

    @abc.abstractmethod
    def list_keywords(self) -> typing.Iterable[URIRef]:
        raise NotImplementedError(f'''
            pls implement list_keywords on {self.__class__.__qualname__}
            to yield URIs of keywords which are used by records in this repository.
        ''')

    @abc.abstractmethod
    def list_pids(self) -> typing.Iterable[URIRef]:
        raise NotImplementedError(f'''
            pls implement list_pids on {self.__class__.__qualname__}:
            to yield persistent identifiers of items/objects/subjects
            noted by records in this repository.
        ''')

    @abc.abstractmethod
    def get_record(self, pid: URIRef, record_format: URIRef) -> bytes:
        raise NotImplementedError(f'''
            pls implement get_record on {self.__class__.__qualname__}:
            to return the requested record as bytes,
            with any further expectations based on record_format
        ''')

    @abc.abstractmethod
    def list_records(self, record_format: URIRef, keyword: typing.Tuple[URIRef] = None) -> typing.Iterable[typing.Tuple[URIRef, bytes]]:
        raise NotImplementedError(f'''
            pls implement list_records on {self.__class__.__qualname__}:
            to yield (uri, record_bytes), with expectations for record_bytes
            based on record_format
        ''')


class OaiPmhRepository:
    NAME = 'SHARE'
    REPOSITORY_IDENTIFIER = 'share.osf.io'
    IDENTIFER_DELIMITER = ':'
    GRANULARITY = 'YYYY-MM-DDThh:mm:ssZ'
    ADMIN_EMAILS = ['share-support@osf.io']

    # TODO better way of structuring this than a bunch of dictionaries?
    # this dictionary's keys are `metadataPrefix` values
    FORMATS = {
        'oai_dc': {
            'formatter_key': 'oai_dc',
            'schema': 'http://www.openarchives.org/OAI/2.0/oai_dc.xsd',
            'namespace': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
        },
    }
    PAGE_SIZE = 20

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

    def resolve_oai_identifier(self, identifier):
        try:
            splid = identifier.split(self.IDENTIFER_DELIMITER)
            if len(splid) != 3 or splid[:2] != ['oai', self.REPOSITORY_IDENTIFIER]:
                raise InvalidID(identifier)
            suid = IDObfuscator.resolve(splid[-1])
            if not isinstance(suid, SourceUniqueIdentifier):
                raise InvalidID(identifier)
            return suid
        except (ObjectDoesNotExist, InvalidID):
            self.errors.append(oai_errors.BadRecordID(identifier))
            return None

    def oai_identifier(self, record):
        if isinstance(record, int):
            share_id = IDObfuscator.encode_id(record, SourceUniqueIdentifier)
        else:
            share_id = IDObfuscator.encode(record.suid)
        return 'oai{delim}{repository}{delim}{id}'.format(id=share_id, repository=self.REPOSITORY_IDENTIFIER, delim=self.IDENTIFER_DELIMITER)

    def _do_identify(self, kwargs, renderer):
        earliest = FormattedMetadataRecord.objects.order_by('date_modified').values_list('date_modified', flat=True)
        return renderer.identify(earliest.first())

    def _do_listmetadataformats(self, kwargs, renderer):
        formats = self.FORMATS

        if 'identifier' in kwargs:
            suid = self.resolve_oai_identifier(kwargs['identifier'])
            formatter_keys = FormattedMetadataRecord.objects.filter(suid=suid).values_list('record_format', flat=True)
            formats = {
                prefix: format_info
                for prefix, format_info in self.FORMATS.items()
                if format_info['formatter_key'] in formatter_keys
            }

        return renderer.listMetadataFormats(formats)

    def _do_listsets(self, kwargs, renderer):
        if 'resumptionToken' in kwargs:
            self.errors.append(oai_errors.BadResumptionToken(kwargs['resumptionToken']))
            return
        return renderer.listSets(
            Source.objects.exclude(is_deleted=True).values_list('name', 'long_title')
        )

    def _do_listidentifiers(self, kwargs, renderer):
        records, next_token = self._load_page(kwargs, just_identifiers=True)
        if self.errors:
            return
        return renderer.listIdentifiers(records, next_token)

    def _do_listrecords(self, kwargs, renderer):
        records, next_token = self._load_page(kwargs, just_identifiers=False)
        if self.errors:
            return
        return renderer.listRecords(records, next_token)

    def _do_getrecord(self, kwargs, renderer):
        suid = self.resolve_oai_identifier(kwargs['identifier'])
        if self.errors:
            return

        record = FormattedMetadataRecord.objects.filter(
            suid=suid,
            record_format=self.FORMATS[kwargs['metadataPrefix']]['formatter_key'],
        ).first()
        if record is None:
            self.errors.append(oai_errors.BadFormatForRecord(kwargs['metadataPrefix']))

        if self.errors:
            return
        return renderer.getRecord(record)

    def _load_page(self, kwargs, just_identifiers):
        if 'resumptionToken' in kwargs:
            try:
                record_queryset, kwargs = self._resume(kwargs['resumptionToken'])
            except (ValueError, KeyError):
                self.errors.append(oai_errors.BadResumptionToken(kwargs['resumptionToken']))
        else:
            record_queryset = self._get_record_queryset(kwargs)
        if self.errors:
            return [], None

        if just_identifiers:
            record_queryset = record_queryset.defer('formatted_metadata')

        records = list(record_queryset)

        if not len(records):
            self.errors.append(oai_errors.NoResults())
            return [], None

        if len(records) <= self.PAGE_SIZE:
            # Last page
            next_token = None
        else:
            records = records[:self.PAGE_SIZE]
            next_token = self._get_resumption_token(kwargs, records[-1].id)
        return records, next_token

    def _get_record_queryset(self, kwargs, catch=True, last_id=None):
        formatter_key = self.FORMATS[kwargs['metadataPrefix']]['formatter_key']

        record_queryset = FormattedMetadataRecord.objects.filter(
            record_format=formatter_key,
        )

        if 'from' in kwargs:
            try:
                from_ = dateutil.parser.parse(kwargs['from'])
                record_queryset = record_queryset.filter(date_modified__gte=from_)
            except ValueError:
                if not catch:
                    raise
                self.errors.append(oai_errors.BadArgument('Invalid value for', 'from'))
        if 'until' in kwargs:
            try:
                until = dateutil.parser.parse(kwargs['until'])
                record_queryset = record_queryset.filter(date_modified__lte=until)
            except ValueError:
                if not catch:
                    raise
                self.errors.append(oai_errors.BadArgument('Invalid value for', 'until'))
        if 'set' in kwargs:
            source_ids = Source.objects.filter(name=kwargs['set']).values_list('id', flat=True)
            record_queryset = record_queryset.filter(
                suid__source_config__source_id__in=source_ids
            )

        # TODO order by... date_modified?
        if last_id is not None:
            record_queryset = record_queryset.filter(id__gt=last_id)

        record_queryset = (
            record_queryset
            .select_related('suid', 'suid__source_config__source')
            .order_by('id')
        )

        if self.errors:
            return None
        # include one extra so we can tell whether this is the last page
        return record_queryset[:self.PAGE_SIZE + 1]

    def _resume(self, token):
        from_, until, set_spec, prefix, last_id = token.split('|')
        kwargs = {}
        if from_:
            kwargs['from'] = from_
        if until:
            kwargs['until'] = until
        if set_spec:
            kwargs['set'] = set_spec
        kwargs['metadataPrefix'] = prefix
        record_queryset = self._get_record_queryset(
            kwargs,
            catch=False,
            last_id=int(last_id),
        )
        return record_queryset, kwargs

    def _get_resumption_token(self, kwargs, last_id):
        from_ = None
        until = None
        if 'from' in kwargs:
            try:
                from_ = dateutil.parser.parse(kwargs['from'])
            except ValueError:
                self.errors.append(oai_errors.BadArgument('Invalid value for', 'from'))
        if 'until' in kwargs:
            try:
                until = dateutil.parser.parse(kwargs['until'])
            except ValueError:
                self.errors.append(oai_errors.BadArgument('Invalid value for', 'until'))
        set_spec = kwargs.get('set', '')
        return self._format_resumption_token(from_, until, set_spec, kwargs['metadataPrefix'], last_id)

    def _format_resumption_token(self, from_, until, set_spec, prefix, last_id):
        # TODO something more opaque, maybe
        return '{}|{}|{}|{}|{}'.format(format_datetime(from_) if from_ else '', format_datetime(until) if until else '', set_spec, prefix, last_id)
