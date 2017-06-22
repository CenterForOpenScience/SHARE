from share.schemas.loader import Schema


schema = Schema.load('./schemas/SHARE/v2/internal/schema.xsd')
state_models = schema.to_django_models(name_tpl='{}State')

for model in state_models:
    locals()[model.__name__] = model

__all__ = tuple(model.__name__ for model in state_models)
