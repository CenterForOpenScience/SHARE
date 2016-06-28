import django_filters

from share.models import ChangeSet, Change

def get_choice_int(val):
    import ipdb
    ipdb.set_trace()
    return getattr(Change.STATUS, val)


class ChangeSetFilter(django_filters.FilterSet):
    status = django_filters.MethodFilter()

    def filter_status(self, queryset, value):
        # django-filters ChoicesFilter doesn't actually work.
        if value and hasattr(Change.STATUS, value):
            return queryset.filter(changes__status=getattr(Change.STATUS, value))
        return queryset


    class Meta:
        model = ChangeSet
        fields = ['submitted_by', 'status']
