import django_filters
import shortuuid

from share.models import ChangeSet, ShareObject


class ObjectIDFilter(django_filters.filters.CharFilter):
    def filter(self, qs, value):
        if value:
            shortuuid.set_alphabet('23456789abcdefghjkmnpqrstuvwxyz')
            value = shortuuid.decode(value)
        return super(ObjectIDFilter, self).filter(qs, value)


class ShareObjectFilterSet(django_filters.FilterSet):
    object_id = ObjectIDFilter(name='uuid')

    class Meta:
        model = ShareObject
        fields = ['object_id',]


class ChangeSetFilterSet(django_filters.FilterSet):
    status = django_filters.MethodFilter()
    target_uuid = django_filters.filters.UUIDFilter(name='changes__share_objects__uuid')
    submitted_by = django_filters.filters.NumberFilter(name='normalized_data__source')

    def filter_status(self, queryset, value):
        # django-filters ChoicesFilter doesn't actually work, at least not with django-model-utils choices
        if value and hasattr(ChangeSet.STATUS, value):
            return queryset.filter(status=getattr(ChangeSet.STATUS, value))
        return queryset


    class Meta:
        model = ChangeSet
        fields = ['submitted_by', 'status', 'target_uuid']
