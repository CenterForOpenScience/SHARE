from datetime import datetime

from django.core.urlresolvers import reverse
from django.views.generic.base import View

from share.models import AbstractCreativeWork


class OAIPMHError(Exception):
    pass


class BadVerbError(OAIPMHError):
    pass




class OAIPMHView(View):
    VERBS = {
        'Identify': 'oaipmh/identify.xml',
    }
    content_type = 'text/xml'

    def get(self, request):
        return self.oai_response(request.GET)

    def post(self, request):
        return self.oai_response(request.POST)

    def oai_response(self, params):
        verb = self.request.GET['verb'].lower()
        if verb == 'identify':
            self.identify(context)
        context.update({
            'verb': verb,
            'response_date': self.format_datetime(datetime.now()),
            'request_url': self.request.build_absolute_uri().rpartition('?')[0],
        })
        return TemplateResponse

    def identify(self, context):
        context.update({
            'repository_name': 'SHARE',
            'base_url': self.request.build_absolute_uri(reverse('oai-pmh')),
            'protocol_version': '2.0',
            'earliest_datestamp': self.format_datetime(AbstractCreativeWork.objects.order_by('date_modified').values_list('date_modified', flat=True)[0]),
            'deleted_record': 'no',
            'granularity': 'YYYY-MM-DDThh:mm:ssZ',
            'admin_emails': ['share-support@osf.io'],
            'identifier_scheme': 'oai',
            'repository_identifier': 'share.osf.io',
            'identifier_delimiter': ':',
            'sample_identifier': 'oai:share.osf.io:461BC-00F-638',
        })

    def format_datetime(self, dt):
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
