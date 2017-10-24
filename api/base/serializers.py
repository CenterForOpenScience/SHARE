from collections import OrderedDict

from rest_framework_json_api import serializers

from api import fields


__all__ = ('ShareSerializer', )


class ShareSerializer(serializers.ModelSerializer):

    # http://stackoverflow.com/questions/27015931/remove-null-fields-from-django-rest-framework-response
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret = OrderedDict(list(filter(lambda x: x[1] is not None, ret.items())))
        return ret
