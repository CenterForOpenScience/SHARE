from rest_framework_json_api import serializers


__all__ = ('ShareSerializer', )


class ShareSerializer(serializers.ModelSerializer):
    pass  # Use as base for all serializers in case we need customizations in the future
