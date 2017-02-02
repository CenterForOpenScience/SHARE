import django_filters
import shortuuid

from share.models import ShareObject


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
        fields = ['object_id', ]
