import django_filters

from share.models import ChangeSet, Change


class ChangeSetFilter(django_filters.FilterSet):
    status = django_filters.MethodFilter()
    target_uuid = django_filters.filters.UUIDFilter(name='changes__share_objects__uuid')

    def filter_status(self, queryset, value):
        # django-filters ChoicesFilter doesn't actually work.
        if value and hasattr(Change.STATUS, value):
            return queryset.filter(changes__status=getattr(Change.STATUS, value))
        return queryset


    class Meta:
        model = ChangeSet
        fields = ['submitted_by', 'status', 'target_uuid']
