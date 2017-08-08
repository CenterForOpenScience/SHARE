import logging
from collections import OrderedDict

from django.core.paginator import Paginator
from django.utils.functional import cached_property

from rest_framework.views import Response
from rest_framework_json_api.pagination import PageNumberPagination
from rest_framework.pagination import CursorPagination

logger = logging.getLogger(__name__)


class FuzzyPaginator(Paginator):

    @cached_property
    def count(self):
        if not hasattr(self.object_list, 'fuzzy_count'):
            logger.warning('%r has no fuzzy_count method. Falling back to a normal count', self.object_list)
            return self.object_list.count()
        return self.object_list.fuzzy_count()


class FuzzyPageNumberPagination(PageNumberPagination):

    django_paginator_class = FuzzyPaginator
    max_page_size = 300


class CursorPagination(CursorPagination):
    ordering = '-id'
    cursor_query_param = 'page[cursor]'

    def get_paginated_response(self, data):
        return Response({
            'results': data,
            'links': OrderedDict([
                ('next', self.get_next_link()),
                ('prev', self.get_previous_link()),
            ])
        })
