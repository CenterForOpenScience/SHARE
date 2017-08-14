from rest_framework import viewsets

from share import models

from api.base.views import ShareViewSet
from api.pagination import CursorPagination
from api.rawdata.serializers import RawDatumSerializer


class RawDataViewSet(ShareViewSet, viewsets.ReadOnlyModelViewSet):
    """
    Raw data, exactly as harvested from the data source.

    ## Query by object
    To get all the raw data corresponding to a Share object, use the query
    parameters `object_id=<@id>` and `object_type=<@type>`
    """

    ordering = ('-id', )
    pagination_class = CursorPagination
    serializer_class = RawDatumSerializer

    def get_queryset(self):
        object_id = self.request.query_params.get('object_id', None)
        object_type = self.request.query_params.get('object_type', None)
        if object_id and object_type:
            return models.RawDatum.objects.filter(
                normalizeddata__changeset__changes__target_id=object_id,
                normalizeddata__changeset__changes__target_type__model=object_type
            ).distinct('id').select_related('suid')
        return models.RawDatum.objects.all().select_related('suid')
