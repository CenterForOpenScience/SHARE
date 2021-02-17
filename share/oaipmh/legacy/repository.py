import dateutil

from django.conf import settings
from django.db import connection

from share.models import AbstractCreativeWork, Source, ShareUser
from share.oaipmh import errors as oai_errors
from share.oaipmh.verbs import OAIVerb
from share.oaipmh.legacy.renderers import OAIRenderer, DublinCoreRenderer
from share.oaipmh.util import format_datetime
from share.util import IDObfuscator, InvalidID


class OAIRepository:
    NAME = 'SHARE'
    REPOSITORY_IDENTIFIER = 'share.osf.io'
    IDENTIFER_DELIMITER = ':'
    GRANULARITY = 'YYYY-MM-DDThh:mm:ssZ'
    ADMIN_EMAILS = ['share-support@osf.io']
    FORMATS = {
        'oai_dc': DublinCoreRenderer,
    }
    PAGE_SIZE = 20

    # extracted from share/search/fetchers.py
    VALID_IDS_QUERY = '''
        SELECT id
        FROM share_creativework
        WHERE id IN %(ids)s
        AND title != ''
        AND (
            SELECT COUNT(*) FROM (
                SELECT * FROM share_workidentifier
                WHERE share_workidentifier.creative_work_id = share_creativework.id
                LIMIT %(max_identifiers)s + 1
            ) AS identifiers
        ) <= %(max_identifiers)s
        AND (
            SELECT COUNT(*) FROM (
                SELECT * FROM share_agentworkrelation
                WHERE share_agentworkrelation.creative_work_id = share_creativework.id
                LIMIT %(max_agent_relations)s + 1
            ) AS agent_relations
        ) <= %(max_agent_relations)s
        ORDER BY id
    '''

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
                work_ids, kwargs = self._resume(kwargs['resumptionToken'])
                metadataRenderer = self._get_metadata_renderer(kwargs['metadataPrefix'], catch=False)
            except (ValueError, KeyError):
                self.errors.append(oai_errors.BadResumptionToken(kwargs['resumptionToken']))
        else:
            work_ids = self._get_record_ids(kwargs)
            metadataRenderer = self._get_metadata_renderer(kwargs['metadataPrefix'])
        if self.errors:
            return [], None, None

        works_queryset = AbstractCreativeWork.objects.filter(
            id__in=work_ids,
        ).include(
            'identifiers',
            'subjects',
            'sources__source',
            'incoming_creative_work_relations',
            'agent_relations__agent',
        ).order_by('id')

        works = list(works_queryset)

        if not len(works):
            self.errors.append(oai_errors.NoResults())
            return [], None, None

        if len(works) <= self.PAGE_SIZE:
            # Last page
            next_token = None
        else:
            works = works[:self.PAGE_SIZE]
            next_token = self._get_resumption_token(kwargs, works[-1].id)
        return works, next_token, metadataRenderer

    def _get_record_ids(self, kwargs, catch=True, last_id=None, page_size=None):
        if page_size is None:
            page_size = self.PAGE_SIZE

        queryset = AbstractCreativeWork.objects.filter(
            is_deleted=False,
            same_as_id__isnull=True,
        )

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
            source_users = ShareUser.objects.filter(source__name=kwargs['set']).values_list('id', flat=True)
            queryset = queryset.filter(sources__in=source_users)

        if last_id is not None:
            queryset = queryset.filter(id__gt=last_id)

        queryset = queryset.order_by('id').values_list('id', flat=True)

        # get some extra, in case some are invalid
        ids = tuple(queryset[:page_size + 10])

        if not ids:
            return []

        # exclude untitled and franken works
        # doing this in a separate query to avoid bad query plans with too much counting
        with connection.cursor() as cursor:
            cursor.execute(
                self.VALID_IDS_QUERY,
                {
                    'ids': ids,
                    'max_identifiers': settings.SHARE_LIMITS['MAX_IDENTIFIERS'],
                    'max_agent_relations': settings.SHARE_LIMITS['MAX_AGENT_RELATIONS'],
                },
            )
            valid_ids = [row[0] for row in cursor.fetchall()]

        # if there were invalid ids, get more to fill out the page
        if len(ids) > page_size and len(valid_ids) <= page_size:
            extra_ids = self._get_record_ids(
                kwargs,
                catch=catch,
                last_id=ids[-1],
                page_size=page_size - len(valid_ids)
            )
            valid_ids.extend(extra_ids)

        return valid_ids[:page_size + 1]

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
        work_ids = self._get_record_ids(kwargs, catch=False, last_id=int(last_id))
        return work_ids, kwargs

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
