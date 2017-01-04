import re

from rest_framework import views
from rest_framework.response import Response

from share import models
from share.models.validators import JSONLDValidator

__all__ = ('SchemaView', 'ModelSchemaView')


INDENT = 4 * ' '
DEFAULT_DOC = r'{}\(.*\)'


class SchemaView(views.APIView):
    def get(self, request, *args, **kwargs):
        schema = JSONLDValidator.jsonld_schema.schema
        return Response(schema)


schema_models = set()


def format_link(model):
    schema_models.add(model)
    link = '- [{0}](/api/schema/{0})'.format(model.__name__)
    if model.__doc__ and not re.fullmatch(DEFAULT_DOC.format(model.__name__), model.__doc__):
        link += ': ' + next(l for l in model.__doc__.splitlines() if l)
    return link


def subclass_links(base_model, include_base=True):
    links = [format_link(base_model)] if include_base else []
    for model in sorted(base_model.__subclasses__(), key=lambda m: m.__name__):
        subclasses = subclass_links(model)
        if include_base:
            subclasses = [INDENT + l for l in subclasses]
        links.extend(subclasses)
    return links


def section(*models):
    return '\n'.join(format_link(m) for m in sorted(models, key=lambda m: m.__name__))


def typed_model(base_model, include_base=True):
    return '\n'.join(subclass_links(base_model, include_base))


SchemaView.__doc__ = """
Schema used to validate changes or additions to the SHARE dataset.

To submit changes, see [`/api/normalizeddata`](/api/normalizeddata)

Each node in the submitted `@graph` is validated by a model schema determined by its `@type`.

## Object schemas

### Work types
{works}

### Agents
{agents}

### Identifiers
{identifiers}

### Other Objects
{others}

## Relation schemas

### Relations between Agents
{agent_relations}

### Relations between Works
{work_relations}

### Relations between Agents and Works
{agentwork_relations}

### Other Relations
{other_relations}
""".format(
    works=typed_model(models.CreativeWork),
    agents=typed_model(models.Agent, include_base=False),
    agent_relations=typed_model(models.AgentRelation, include_base=False),
    work_relations=typed_model(models.WorkRelation, include_base=False),
    agentwork_relations=typed_model(models.AgentWorkRelation, include_base=False),
    identifiers=section(models.WorkIdentifier, models.AgentIdentifier),
    others=section(models.Award, models.Subject, models.Tag),
    other_relations=section(models.ThroughAwards, models.ThroughContributor, models.ThroughSubjects, models.ThroughTags),
)


class ModelSchemaView(views.APIView):
    """
    Schema used to validate submitted changes with `@type='{}'`. See [`/api/schema`](/api/schema)

    {}
    """
    model_views = []

    def get(self, request, *args, **kwargs):
        schema = JSONLDValidator().validator_for(self.MODEL).schema
        return Response(schema)


for model in schema_models:
    name = '{}SchemaView'.format(model.__name__)
    ModelSchemaView.model_views.append(type(name, (ModelSchemaView,), {
        'MODEL': model,
        '__doc__': ModelSchemaView.__doc__.format(model.__name__, model.__doc__)
    }))
