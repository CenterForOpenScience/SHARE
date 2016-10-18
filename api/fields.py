import shortuuid
from rest_framework import serializers
from rest_framework.reverse import reverse


class TypeField(serializers.ReadOnlyField):
    """
    Returns the type of a model by getting the model_name from the model's metaclass.
    """
    def get_attribute(self, instance):
        return instance

    def to_representation(self, obj):
        return obj._meta.model_name


class ObjectIDField(serializers.ReadOnlyField):
    """
    Returns a cleaner version of a uuid
    """

    def get_attribute(self, instance):
        return instance

    def to_representation(self, value):
        shortuuid.set_alphabet('23456789abcdefghjkmnpqrstuvwxyz')
        return shortuuid.encode(value.uuid)


class DetailUrlField(serializers.ReadOnlyField):
    """
    Returns an object's @id, the url to its detail page.
    e.g. 'http://share.osf.io/api/v2/preprints/18'
    """

    def get_attribute(self, instance):
        return instance

    def to_representation(self, obj):
        model = obj._meta.model_name
        if 'version' in model:
            model = model[:-7]
        view = 'api:{}-detail'.format(model)
        request = self.context['request']
        return reverse(view, kwargs={'pk': obj.id}, request=request)


class LinksField(serializers.ReadOnlyField):
    """
    Returns a dictionary of links to an object's relationships.
    """

    def __init__(self, **kwargs):
        self._links = kwargs.pop('links', ())
        super(serializers.ReadOnlyField, self).__init__(**kwargs)

    def get_attribute(self, instance):
        return instance

    def to_representation(self, obj):
        request = self.context['request']
        return {
            l: reverse('api:{}-{}'.format(obj._meta.model_name, l), kwargs={'pk': obj.id}, request=request)
            for l in self._links
        }
