import django_filters

from share.models import ChangeSet, Change


class ChangeSetFilter(django_filters.FilterSet):
    status = django_filters.MethodFilter()
    target_uuid = django_filters.filters.UUIDFilter(name='changes__share_objects__uuid')


    def filter_status(self, queryset, value):
        # django-filters ChoicesFilter doesn't actually work, at least not with django-model-utils choices
        if value and hasattr(ChangeSet.STATUS, value):
            return queryset.filter(status=getattr(ChangeSet.STATUS, value))
        return queryset


    class Meta:
        model = ChangeSet
        fields = ['submitted_by', 'status', 'target_uuid']
