from rest_framework import viewsets

from share.models.jobs import IngestJob

from api.base.views import ShareViewSet
from api.pagination import CursorPagination
from api.ingestjobs.serializers import IngestJobSerializer


class IngestJobViewSet(ShareViewSet, viewsets.ReadOnlyModelViewSet):
    ordering = ('-id', )

    serializer_class = IngestJobSerializer
    pagination_class = CursorPagination

    def get_queryset(self):
        return IngestJob.objects.all()
