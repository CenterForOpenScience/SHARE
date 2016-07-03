from rest_framework import serializers


class TypeField(serializers.ReadOnlyField):
    """
    Returns the type of a model by getting the model_name from the model's metaclass.
    """
    def get_attribute(self, instance):
        return instance

    def to_representation(self, obj):
        return obj._meta.model_name
