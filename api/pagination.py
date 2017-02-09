from django.core.paginator import Paginator
from django.utils.functional import cached_property

from rest_framework_json_api.pagination import PageNumberPagination


class FuzzyPaginator(Paginator):

    @cached_property
    def count(self):
        return self.object_list.fuzzy_count()


class FuzzyPageNumberPagination(PageNumberPagination):

    django_paginator_class = FuzzyPaginator
