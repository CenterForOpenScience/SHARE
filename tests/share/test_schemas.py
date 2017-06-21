from share.schemas.loader import Schema


class TestSchemaLoader:

    def test_load(self):
        schema = Schema.load('./schemas/SHARE/v2/internal/schema.xsd')
        schema.to_django_models(name_tpl='{}State')
