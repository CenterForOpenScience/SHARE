import uuid
from functools import reduce

from django.apps import apps
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist

from share.normalize.links import Context
from share.normalize.links import AbstractLink
from share.normalize.utils import format_doi_as_url


# NOTE: Context is a thread local singleton
# It is asigned to ctx here just to keep a family interface
ctx = Context()


class ParserMeta(type):

    def __new__(cls, name, bases, attrs):
        # Enabled inheritance in parsers.
        parsers = reduce(lambda acc, val: {**acc, **getattr(val, 'parsers', {})}, bases[::-1], {})
        for key, value in tuple(attrs.items()):
            if isinstance(value, AbstractLink):
                parsers[key] = attrs.pop(key).chain()[0]
        attrs['parsers'] = parsers

        attrs['_extra'] = reduce(lambda acc, val: {**acc, **getattr(val, '_extra', {})}, bases[::-1], {})
        attrs['_extra'].update({
            key: value.chain()[0]
            for key, value
            in attrs.pop('Extra', object).__dict__.items()
            if isinstance(value, AbstractLink)
        })

        return super(ParserMeta, cls).__new__(cls, name, bases, attrs)


class Parser(metaclass=ParserMeta):

    @classmethod
    def using(cls, **overrides):
        if not all(isinstance(x, AbstractLink) for x in overrides.values()):
            raise Exception('Found non-link values in {}. Maybe you need to wrap something in Delegate?'.format(overrides))
        return type(
            cls.__name__ + 'Overridden',
            (cls, ), {
                'schema': cls.schema if isinstance(cls.schema, str) else cls.__name__.lower(),
                **overrides
            }
        )

    @property
    def schema(self):
        return self.__class__.__name__.lower()

    @property
    def model(self):
        return apps.get_model('share', self.schema)

    def __init__(self, context, config=None):
        self.config = config or ctx._config
        self.context = context
        self.id = '_:' + uuid.uuid4().hex
        self.ref = {'@id': self.id, '@type': self.schema}

    def validate(self, field, value):
        if field.is_relation:
            if field.rel.many_to_many:
                assert isinstance(value, (list, tuple)), 'Values for field {} must be lists. Found {}'.format(field, value)
            else:
                assert isinstance(value, dict) and '@id' in value and '@type' in value, 'Values for field {} must be a dictionary with keys @id and @type. Found {}'.format(field, value)
        else:
            assert not isinstance(value, dict), 'Value for non-relational field {} must be a primative type. Found {}'.format(field, value)

    def parse(self):
        if (self.context, self.schema) in ctx.pool:
            return ctx.pool[self.context, self.schema]

        inst = {**self.ref}  # Shorthand for copying inst
        ctx.pool[self.context, self.schema] = self.ref

        prev, Context().parser = Context().parser, self

        for key, chain in self.parsers.items():
            try:
                field = self.model._meta.get_field(key)
            except FieldDoesNotExist:
                raise Exception('Tried to parse value {} which does not exist on {}'.format(key, self.model))

            value = chain.run(self.context)

            if value and field.is_relation and field.rel.many_to_many:
                for v in value:
                    ctx.pool[v][field.m2m_field_name()] = self.ref

            if value is not None:
                self.validate(field, value)
                inst[key] = value

        inst['extra'] = {}
        for key, chain in self._extra.items():
            val = chain.run(self.context)
            if val:
                inst['extra'][key] = val
        if not inst['extra']:
            del inst['extra']

        Context().parser = prev

        ctx.pool[self.ref] = inst
        ctx.graph.append(inst)

        # Return only a reference to the parsed object to avoid circular data structures
        return self.ref


# Some common, reusable parsers with redundant names that repeat a word


class URIIdentifier(Parser):
    schema = 'Identifier'
    url = ctx
    base_url = RunPython('get_base_url', ctx)

    def get_base_url(self, url):
        url = furl.furl(url)
        return '{}://{}'.format(url.scheme, url.host)


class DOIIdentifier(Parser):
    schema = 'Identifier'
    url = RunPython('format_doi_as_url', ctx),
    base_url = Static(settings.DOI_BASE_URL)

    def format_doi_as_url(self, doi):
        return format_doi_as_url(self, doi)

