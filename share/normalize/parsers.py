import uuid

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

        return super(ParserMeta, cls).__new__(cls, name, bases, attrs)


class Subparser:
    def __init__(self, name, is_list=False):
        self._name = name
        self._is_list = is_list

    def resolve(self, parent, value):
        prev, ctx.parent = ctx.parent, parent.context
        # Peak into the module where all the parsers are being importted from
        # and look for one matching out name
        # TODO Add a way to explictly declare the parser to be used. For more generic formats
        klass = getattr(parent.__class__, self._name, None) or getattr(__import__(parent.__module__, fromlist=(self._name,)), self._name)
        if self._is_list:
            ret = [klass(v).parse() for v in value]
        else:
            ret = klass(value).parse()
        # Reset the parent to avoid leaking into other parsers
        ctx.parent = prev
        return ret


class AbstractParser(metaclass=ParserMeta):
    subparsers = {}

    def __init__(self, context):
        self.context = context
        self._value = ctx.pool.get((context, self.__class__.__name__))

    def parse(self):
        if self._value:
            return self._value

        inst = {'@id': '_:' + uuid.uuid4().hex, '@type': self.__class__.__name__}

        ctx.pool[(self.context, inst['@type'])] = inst

        # Splats result in a new dict; the instance in ctx.pool will not be mutated
        inst = {**inst, **{
            key: (key in self.subparsers and self.subparsers[key].resolve(self, chain.execute(self.context))) or chain.execute(self.context)
            for key, chain in self.parsers.items()
        }}

        ctx.graph.append(inst)

        # Return only a reference to the parsed object to avoid circular data structures
        return {'@id': inst['@id'], '@type': inst['@type']}


class AbstractOrganization(AbstractParser):
    pass


class AbstractAffiliation(AbstractParser):
    person = ctx['parent']
    subparsers = {'organization': Subparser('Organization'), 'person': Subparser('Person')}


class AbstractEmail(AbstractParser):
    pass


class AbstractPerson(AbstractParser):
    subparsers = {'affiliations': Subparser('Affiliation', is_list=True)}


class AbstractManuscript(AbstractParser):
    subparsers = {'contributors': Subparser('Contributor', is_list=True)}


class AbstractContributor(AbstractParser):
    manuscript = ctx['parent']
    subparsers = {'person': Subparser('Person'), 'manuscript': Subparser('Manuscript')}
