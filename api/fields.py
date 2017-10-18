from rest_framework import serializers

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


class ObfuscatedIDField(serializers.ReadOnlyField):

    def get_attribute(self, instance):
        return instance

    def to_representation(self, instance):
        return IDObfuscator.encode(instance)

    def to_internal_value(self, value):
        try:
            return IDObfuscator.decode_id(value)[1]
        except InvalidID:
            raise serializers.ValidationError('Invalid ID')
