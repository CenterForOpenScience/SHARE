from django.db import models

from share.schemas.loader import Schema
from share.schemas.constructor import ModelConstructor


class AbstractSchemaState(models.Model):
    source_identifier = models.ForeignKey('SourceUniqueIdentifier')

    class Meta:
        abstract = True


schema = Schema.load('./schemas/SHARE/v2/internal/schema.yaml')
state_models = ModelConstructor(schema, name_tpl='{}State', base=AbstractSchemaState, module=__name__)

state_models.construct()

for model in state_models:
    locals()[model.__name__] = model

__all__ = tuple(model.__name__ for model in state_models)
