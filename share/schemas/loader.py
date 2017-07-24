import logging
import collections

from ruamel.yaml import YAML

from django.utils.six import _import_module


yaml = YAML(typ='safe')
logger = logging.getLogger(__name__)


class Schema:
    yaml_tag = '!python/share.schema.Schema'

    @classmethod
    def from_yaml(cls, constructor, node):
        parsed = constructor.construct_mapping(node, deep=True)
        return cls(parsed['name'], parsed['types'])

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict({
            'name': node.name,
            'types': list(node.types.values()),
        })

    @classmethod
    def load(cls, path):
        logger.debug('Opening %s', path)
        with open(path, 'r') as fobj:
            schema = yaml.load(fobj)
            if not isinstance(schema, cls):
                raise ValueError('{!r} is not of type {!r}'.format(schema, cls))
            return schema

    def __init__(self, name, types):
        self.name = name
        self.types = collections.OrderedDict([(st.name, st) for st in types])


class SchemaType:
    yaml_tag = '!python/share.schema.SchemaType'

    @classmethod
    def from_yaml(cls, constructor, node):
        (parsed, ) = constructor.construct_yaml_omap(node)
        return cls(parsed['name'], parsed.get('description'), parsed['fields'], parsed.get('meta'))

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_omap(cls.yaml_tag, collections.OrderedDict([
            ('name', node.name),
            ('description', node.description),
            ('fields', node.fields)
        ]))

    def __init__(self, name, description=None, fields=(), meta=None):
        self.description = description
        self.fields = fields
        self.name = name
        self.meta = meta or {}

    def to_django_model(self, constructor):
        attrs = {name.replace('-', '_'): field.to_django_field(constructor) for name, field in self.fields.items()}
        attrs['__module__'] = constructor.module
        attrs['Meta'] = type('Meta', (), {**self.meta, **constructor.meta_for(self)})
        return type(constructor.name_for(self), (constructor.base, ), attrs)


class SchemaField:
    yaml_tag = '!python/share.schema.SchemaField'

    @classmethod
    def from_yaml(cls, constructor, node):
        parsed = constructor.construct_mapping(node)
        return cls(parsed.pop('type'), **parsed)

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_mapping(cls.yaml_tag, {'type': node.type, **node.options})

    @property
    def is_relation(self):
        return self.options.get('to') is not None

    @property
    def related(self):
        return self.options['to']

    def __init__(self, type, **kwargs):
        self.type = type
        self.options = kwargs

    def to_django_field(self, constructor):
        mod_name, _, name = self.type.rpartition('.')
        mod = _import_module(mod_name)
        options = self.options.copy()

        if self.is_relation:
            options['to'] = constructor.name_for(constructor.schema.types[options['to']])

        if 'choices' in self.options:
            options['choices'] = [(choice.lower().title(), choice.lower()) for choice in options['choices']]

        return getattr(mod, name)(**options)


yaml.register_class(Schema)
yaml.register_class(SchemaType)
yaml.register_class(SchemaField)
