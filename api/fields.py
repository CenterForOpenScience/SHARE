from rest_framework_json_api import serializers
from rest_framework.utils.field_mapping import get_detail_view_name

from share.util import IDObfuscator
from share.util import InvalidID


class TypeField(serializers.ReadOnlyField):
    """
    Returns the type of a model by getting the model_name from the model's metaclass.
    """
    def get_attribute(self, instance):
        return instance

    def to_representation(self, obj):
        return obj._meta.model_name


class ShareIdentityField(serializers.HyperlinkedIdentityField):

    def get_object(self, view_name, view_args, view_kwargs):
        obfuscated_id = view_kwargs[self.lookup_url_kwarg]
        return IDObfuscator.resolve(obfuscated_id)

    def get_url(self, obj, view_name, request, format):
        obfuscated_id = IDObfuscator.encode(obj)
        kwargs = {self.lookup_url_kwarg: obfuscated_id}
        return self.reverse(view_name, kwargs=kwargs, request=request, format=format)
