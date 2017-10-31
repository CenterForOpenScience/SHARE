from rest_framework_json_api import serializers

from share import models

from api.base import ShareSerializer


class SiteBannerSerializer(ShareSerializer):
    color = serializers.SerializerMethodField()

    def get_color(self, obj):
        return models.SiteBanner.COLOR[obj.color]

    class Meta:
        model = models.SiteBanner
        fields = ('title', 'description', 'color', 'icon')
