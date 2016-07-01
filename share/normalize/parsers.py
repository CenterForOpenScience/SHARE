import uuid

from django.apps import apps
from django.core.exceptions import FieldDoesNotExist

from share.normalize.links import Context
from share.normalize.links import AbstractLink


# NOTE: Context is a thread local singleton
# It is asigned to ctx here just to keep a family interface
ctx = Context()


class ParserMeta(type):

    def __new__(cls, name, bases, attrs):
        # Enabled inheirtence in parsers.
        parsers = {**bases[0].parsers} if bases else {}
        for key, value in tuple(attrs.items()):
            if isinstance(value, AbstractLink):
                # Only need the AnchorLink to call the parser
                parsers[key] = attrs.pop(key).chain()[0]
        attrs['parsers'] = parsers

        attrs['_extra'] = {
            key: value.chain()[0]
            for key, value
            in attrs.pop('Extra', object).__dict__.items()
            if isinstance(value, AbstractLink)
        }

        return super(ParserMeta, cls).__new__(cls, name, bases, attrs)


class Subparser:

    @property
    def model(self):
        if self.field.many_to_many:
            return self.field.rel.through
        return self.field.rel.model

    @property
    def is_list(self):
        return self.field.many_to_many

    @property
    def parser(self):
        # Peek into the module where all the parsers are being imported from
        # and look for one matching out name
        # TODO Add a way to explictly declare the parser to be used. For more generic formats
        if hasattr(self.parent.__class__, self.model.__name__):
            return getattr(self.parent, self.model.__name__)
        return getattr(__import__(self.parent.__module__, fromlist=(self.model.__name__,)), self.model.__name__)

    def __init__(self, field, parent, context):
        self.field = field
        self.parent = parent
        self.context = context

    def resolve(self):
        prev, ctx.parent = ctx.parent, self.context

        if self.is_list:
            ret = [self.parser(v).parse() for v in self.context or []]
        else:
            ret = self.parser(self.context).parse()

        # Reset the parent to avoid leaking into other parsers
        ctx.parent = prev
        return ret


class Parser(metaclass=ParserMeta):

    @property
    def schema_type(self):
        return getattr(self.__class__, 'schema', self.__class__.__name__.lower())

    @property
    def model(self):
        return apps.get_model('share', self.schema_type)

    def __init__(self, context):
        self.context = context
        self.id = '_:' + uuid.uuid4().hex

        self._value = ctx.pool.get((context, self.schema_type))

    def parse(self):
        if self._value:
            return self._value

        ref = {'@id': self.id, '@type': self.schema_type}
        ctx.pool[(self.context, self.schema_type)] = ref

        inst = {**ref}  # Shorthand for copying inst

        for key, chain in self.parsers.items():
            value = chain.execute(self.context)

            try:
                field = self.model._meta.get_field(key)
            except FieldDoesNotExist:
                raise Exception('Tried to parse value {} which does not exist on {}'.format(key, self.model))

            if field.is_relation:
                value = Subparser(field, self, value).resolve()
                if field.rel.many_to_many:
                    for v in value:
                        ctx.pool[v][field.m2m_field_name()] = ref

            inst[key] = value

        if self._extra:
            inst['extra'] = {key: chain.execute(self.context) for key, chain in self._extra.items()}

        ctx.pool[ref] = inst
        ctx.graph.append(inst)

        # Return only a reference to the parsed object to avoid circular data structures
        return ref
