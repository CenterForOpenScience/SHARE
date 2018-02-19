from rest_framework_json_api import serializers

from share import models

from api.base import ShareSerializer
from api.fields import ShareIdentityField


class IngestJobSerializer(ShareSerializer):
    # link to self
    url = ShareIdentityField(view_name='api:ingestjob-detail')

    status = serializers.SerializerMethodField()

    class Meta:
        model = models.IngestJob
        fields = (
            'status',
            'error_message',
            'error_type',
            'completions',
            'date_started',
            'date_created',
            'date_modified',
            'raw',
            'source_config',
            'url'
        )

    def get_status(self, job):
        return job.STATUS[job.status]
