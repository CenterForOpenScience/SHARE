from datetime import datetime

from django.core.urlresolvers import reverse
from django.views.generic.base import View
from django.template.response import SimpleTemplateResponse

from share.models import AbstractCreativeWork, Source
from share.oaipmh import errors as oai_errors, formats
from share.oaipmh.util import format_datetime
from share.util import IDObfuscator, InvalidID


class OAIVerb:
    def __init__(self, template, required_args=(), optional_args=(), exclusive_arg=None):
        self.template = template
        self.required_args = set(required_args)
        self.optional_args = set(optional_args)
        self.exclusive_arg = exclusive_arg

    def validate(self, kwargs):
        keys = set(kwargs.keys())
        errors = []

        if self.exclusive_arg and self.exclusive_arg in keys and (len(keys) > 1 or len(keys[self.exclusive_arg]) > 1):
            errors.append(oai_errors.BadArgument('Exclusive', self.exclusive_arg))

        missing = self.required_args - keys
        for arg in missing:
            errors.append(oai_errors.BadArgument('Required', arg))

        illegal = keys - self.required_args - self.optional_args - set([self.exclusive_arg])
        for arg in illegal:
            errors.append(oai_errors.BadArgument('Illegal', arg))

        repeated = [k for k, v in kwargs.items() if len(v) > 1]
        for arg in repeated:
            errors.append(oai_errors.BadArgument('Repeated', arg))

        return errors


class OAIPMHView(View):
    REPOSITORY_IDENTIFIER = 'share.osf.io'
    IDENTIFER_DELIMITER = ':'
    CONTENT_TYPE = 'text/xml'
    FORMATS = [
        formats.DublinCoreFormat,
    ]
    VERBS = {
        'Identify': OAIVerb('oaipmh/identify.xml'),
        'ListMetadataFormats': OAIVerb('oaipmh/listformats.xml', optional_args=('identifier',)),
        'GetRecord': OAIVerb('oaipmh/getrecord.xml', required_args=('identifier', 'metadataPrefix')),
        'ListSets': OAIVerb('oaipmh/listsets.xml', exclusive_arg='resumptionToken'),
    }
    ERROR_TEMPLATE = 'oaipmh/error.xml'

    def get(self, request):
        return self.oai_response(**request.GET)

    def post(self, request):
        return self.oai_response(**request.POST)

    def oai_response(self, **kwargs):
        self.errors = []
        self.context = {
            'response_date': format_datetime(datetime.now()),
            'request_url': self.request.build_absolute_uri().rpartition('?')[0],
        }
        verb_name = kwargs.pop('verb', [])
        if not verb_name or len(verb_name) > 1 or verb_name[0] not in self.VERBS:
            self.errors.append(oai_errors.BadVerb(verb_name))
        else:
            verb_name = verb_name[0]
            self.context['verb'] = verb_name
            verb = self.VERBS[verb_name]
            self.errors.extend(verb.validate(kwargs))
            if not self.errors:
                # No repeated arguments at this point
                kwargs = {k: v[0] for k, v in kwargs.items()}
                self.context['kwargs'] = kwargs
                template = verb.template
                getattr(self, '_do_{}'.format(verb_name.lower()))(kwargs)

        if self.errors:
            self.context['errors'] = self.errors
            template = self.ERROR_TEMPLATE
        return SimpleTemplateResponse(template, context=self.context, content_type=self.CONTENT_TYPE)

    def _do_identify(self, kwargs):
        self.context.update({
            'repository_name': 'SHARE',
            'base_url': self.request.build_absolute_uri(reverse('oai-pmh')),
            'protocol_version': '2.0',
            'earliest_datestamp': format_datetime(AbstractCreativeWork.objects.order_by('date_modified').values_list('date_modified', flat=True)[0]),
            'deleted_record': 'no',
            'granularity': 'YYYY-MM-DDThh:mm:ssZ',
            'admin_emails': ['share-support@osf.io'],
            'identifier_scheme': 'oai',
            'repository_identifier': self.REPOSITORY_IDENTIFIER,
            'identifier_delimiter': self.IDENTIFER_DELIMITER,
            'sample_identifier': self.oai_identifier(1),
        })

    def _do_listmetadataformats(self, kwargs):
        self.context['formats'] = self.FORMATS

    def _do_listsets(self, kwargs):
        if 'resumptionToken' in kwargs:
            self.errors.append(oai_errors.BadResumptionToken(kwargs['resumptionToken']))
            return
        self.context['sets'] = Source.objects.values_list('name', 'long_title')

    def _do_getrecord(self, kwargs):
        try:
            prefix = kwargs['metadataPrefix']
            format = next(f for f in self.FORMATS if f.prefix == prefix)()
        except StopIteration:
            self.errors.append(oai_errors.BadFormat(prefix))

        work = self.resolve_oai_identifier(kwargs['identifier'])
        if self.errors:
            return
        self.context.update({
            **self._record_header_context(work),
            'format': format,
            'work': format.work_context(work, self),
        })

    def oai_identifier(self, work):
        if isinstance(work, int):
            share_id = IDObfuscator.encode_id(work, AbstractCreativeWork)
        else:
            share_id = IDObfuscator.encode(work)
        return 'oai{delim}{repository}{delim}{id}'.format(id=share_id, repository=self.REPOSITORY_IDENTIFIER, delim=self.IDENTIFER_DELIMITER)

    def resolve_oai_identifier(self, identifier):
        try:
            splid = identifier.split(self.IDENTIFER_DELIMITER)
            if len(splid) != 3 or splid[:2] != ['oai', self.REPOSITORY_IDENTIFIER]:
                raise InvalidID(identifier)
            return IDObfuscator.resolve(splid[-1])
        except (AbstractCreativeWork.DoesNotExist, InvalidID):
            self.errors.append(oai_errors.BadRecordID(identifier))
            return None

    def _record_header_context(self, work):
        return {
            'oai_identifier': self.oai_identifier(work),
            'datestamp': format_datetime(work.date_modified),
            'set_specs': work.sources.values_list('source__name', flat=True),
        }
