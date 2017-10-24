from api.base.serializers import ShareSerializer


class ShareObjectSerializer(ShareSerializer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # remove hidden fields
        excluded_fields = ['change', 'sources']
        for field_name in tuple(self.fields.keys()):
            if 'version' in field_name or field_name in excluded_fields:
                self.fields.pop(field_name)
