from django.db import models

from share.schemas.loader import Schema
from share.schemas.contructor import ModelConstructor


class TestSchemas:

    def test_load(self):
        schema = Schema.load('./schemas/SHARE/v2/internal/schema.xsd')

        assert schema.types

    def test_constructor(self):
        schema = Schema.load('./schemas/SHARE/v2/internal/schema.xsd')
        constructor = ModelConstructor(schema, name_tpl='{}Test')

        constructor.construct()

        for model in constructor:
            assert issubclass(model, models.Model)
            assert model.__name__.endswith('Test')
