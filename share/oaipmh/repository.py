import dateutil

from share.models import AbstractCreativeWork, Source
from share.oaipmh import errors as oai_errors, renderers
from share.oaipmh.verbs import OAIVerb
from share.oaipmh.renderers import OAIRenderer
from share.oaipmh.util import format_datetime
from share.util import IDObfuscator, InvalidID


class OAIRepository:
    NAME = 'SHARE'
    REPOSITORY_IDENTIFIER = 'share.osf.io'
    IDENTIFER_DELIMITER = ':'
    GRANULARITY = 'YYYY-MM-DDThh:mm:ssZ'
    ADMIN_EMAILS = ['share-support@osf.io']
    FORMATS = {
        'oai_dc': renderers.DublinCoreRenderer,
    }
    PAGE_SIZE = 100

    def handle_request(self, request, kwargs):
        renderer = OAIRenderer(self, request)
        verb, self.errors = OAIVerb.validate(**kwargs)
        if not self.errors:
            # No repeated arguments at this point
            kwargs = {k: v[0] for k, v in kwargs.items()}
            renderer.kwargs = kwargs
            xml = getattr(self, '_do_{}'.format(verb.name.lower()))(kwargs, renderer)

        return xml if not self.errors else renderer.errors(self.errors)

    def resolve_oai_identifier(self, identifier):
        try:
            splid = identifier.split(self.IDENTIFER_DELIMITER)
            if len(splid) != 3 or splid[:2] != ['oai', self.REPOSITORY_IDENTIFIER]:
                raise InvalidID(identifier)
            return IDObfuscator.resolve(splid[-1])
        except (AbstractCreativeWork.DoesNotExist, InvalidID):
            self.errors.append(oai_errors.BadRecordID(identifier))
            return None

    def oai_identifier(self, work):
        if isinstance(work, int):
            share_id = IDObfuscator.encode_id(work, AbstractCreativeWork)
        else:
            share_id = IDObfuscator.encode(work)
        return 'oai{delim}{repository}{delim}{id}'.format(id=share_id, repository=self.REPOSITORY_IDENTIFIER, delim=self.IDENTIFER_DELIMITER)

    def _do_identify(self, kwargs, renderer):
        earliest = AbstractCreativeWork.objects.order_by('date_modified').values_list('date_modified', flat=True)
        return renderer.identify(earliest[0] if earliest.exists() else None)

    def _do_listmetadataformats(self, kwargs, renderer):
        if 'identifier' in kwargs:
            self.resolve_oai_identifier(kwargs['identifier'])
        return renderer.listMetadataFormats(self.FORMATS)

    def _do_listsets(self, kwargs, renderer):
        if 'resumptionToken' in kwargs:
            self.errors.append(oai_errors.BadResumptionToken(kwargs['resumptionToken']))
            return
        return renderer.listSets(Source.objects.values_list('name', 'long_title'))

    def _do_listidentifiers(self, kwargs, renderer):
        works, next_token, _ = self._load_page(kwargs)
        if self.errors:
            return
        return renderer.listIdentifiers(works, next_token)

    def _do_listrecords(self, kwargs, renderer):
        works, next_token, metadataRenderer = self._load_page(kwargs)
        if self.errors:
            return
        return renderer.listRecords(works, next_token, metadataRenderer)

    def _do_getrecord(self, kwargs, renderer):
        metadataRenderer = self._get_metadata_renderer(kwargs['metadataPrefix'])
        work = self.resolve_oai_identifier(kwargs['identifier'])
        if self.errors:
            return
        return renderer.getRecord(work, metadataRenderer)

    def _get_metadata_renderer(self, prefix, catch=True):
        try:
            return self.FORMATS[prefix](self)
        except KeyError:
            if not catch:
                raise
            self.errors.append(oai_errors.BadFormat(prefix))

    def _load_page(self, kwargs):
        if 'resumptionToken' in kwargs:
            try:
                queryset, next_token, format, cursor = self._resume(kwargs['resumptionToken'])
            except (ValueError, KeyError):
                self.errors.append(oai_errors.BadResumptionToken(kwargs['resumptionToken']))
        else:
            queryset = self._record_queryset(kwargs)
            next_token = self._get_resumption_token(kwargs)
            metadataRenderer = self._get_metadata_renderer(kwargs['metadataPrefix'])
            cursor = 0
        if self.errors:
            return [], None, None
        if not queryset.exists():
            self.errors.append(oai_errors.NoResults())
            return [], None, None
        # TODO is there a way to prefetch Sources/Relations/Identifiers just for this slice? https://code.djangoproject.com/ticket/26780
        works = queryset[cursor:cursor + self.PAGE_SIZE + 1]
        if len(works) > self.PAGE_SIZE:
            works = works[:self.PAGE_SIZE]
        else:
            next_token = None
        return works, next_token, metadataRenderer

    def _record_queryset(self, kwargs, catch=True):
        queryset = AbstractCreativeWork.objects.filter(is_deleted=False, same_as_id__isnull=True)
        if 'from' in kwargs:
            try:
                from_ = dateutil.parser.parse(kwargs['from'])
                queryset = queryset.filter(date_modified__gte=from_)
            except ValueError:
                if not catch:
                    raise
                self.errors.append(oai_errors.BadArgument('Invalid value for', 'from'))
        if 'until' in kwargs:
            try:
                until = dateutil.parser.parse(kwargs['until'])
                queryset = queryset.filter(date_modified__lte=until)
            except ValueError:
                if not catch:
                    raise
                self.errors.append(oai_errors.BadArgument('Invalid value for', 'until'))
        if 'set' in kwargs:
            queryset = queryset.filter(sources__source__name=kwargs['set'])

        return queryset

    def _resume(self, token):
        from_, until, set_spec, prefix, cursor = token.split('|')
        kwargs = {}
        if from_:
            kwargs['from'] = from_
        if until:
            kwargs['until'] = until
        if set_spec:
            kwargs['set'] = set_spec
        cursor = int(cursor)
        queryset = self._record_queryset(kwargs, catch=False)
        kwargs['cursor'] = cursor + self.PAGE_SIZE
        kwargs['metadataPrefix'] = prefix
        next_token = self._get_resumption_token(kwargs)
        metadataRenderer = self._get_metadata_renderer(prefix, catch=False)
        return queryset, next_token, metadataRenderer, cursor

    def _get_resumption_token(self, kwargs):
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
        cursor = kwargs.get('cursor', self.PAGE_SIZE)
        return self._format_resumption_token(from_, until, set_spec, kwargs['metadataPrefix'], cursor)

    def _format_resumption_token(self, from_, until, set_spec, prefix, cursor):
        # TODO something more opaque, maybe
        return '{}|{}|{}|{}|{}'.format(format_datetime(from_) if from_ else '', format_datetime(until) if until else '', set_spec, prefix, cursor)
