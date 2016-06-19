import uuid
import threading
from functools import reduce
from collections import deque

import dateparser

from lxml import etree

from nameparser import HumanName

import share.models


__all__ = (
    'ctx',
    'Concat',
    'ParseDate',
    'ParseName',
    'AbstractPerson',
    'AbstractEmail',
    'AbstractManuscript',
    'AbstractOrganization',
    'AbstractAffiliation',
    'AbstractContributor',
)


class DictHashingDict:

    def __init__(self):
        self.__inner = {}

    def get(self, key, *args):
        return self.__inner.get((self._hash(key[0]), key[1]), *args)

    def __getitem__(self, key):
        return self.__inner[(self._hash(key[0]), key[1])]

    def __setitem__(self, key, value):
        self.__inner[(self._hash(key[0]), key[1])] = value

    def _hash(self, val):
        if isinstance(val, dict):
            val = tuple((k, self._hash(v)) for k, v in val.items())
        if isinstance(val, list):
            val = tuple(self._hash(v) for v in val)
        return val


class AbstractLink:

    def __init__(self, _next=None, _prev=None):
        self._next = _next
        self._prev = _prev

    def chain(self):
        first = self
        while first._prev:
            first = first._prev
        deq = deque([first])
        while deq[-1]._next:
            deq.append(deq[-1]._next)
        return tuple(deq)

    def execute(self, obj):
        raise NotImplemented

    def text(self):
        return self + TextLink()

    def __add__(self, step):
        self._next = step
        step._prev = self
        return step

    def __getitem__(self, name):
        if name == '*':
            return self + IteratorLink()
        if name == 'parent':
            return self + ParentLink()
        if isinstance(name, int):
            return self + IndexLink(name)
        raise Exception

    def __call__(self, name):
        return self + PathLink(name)

    def __getattr__(self, name):
        return self + PathLink(name)


class AnchorLink(AbstractLink):

    def __init__(self, split=True):
        self._split = split
        super().__init__()

    def execute(self, obj):
        return reduce(lambda acc, cur: cur.execute(acc), self.chain()[1:], obj)

    def __add__(self, step):
        if not self._split:
            return super().__add__(step)
        return AnchorLink(split=False) + step


class Context(AnchorLink):

    __CONTEXT = threading.local()

    @property
    def graph(self):
        return Context.__CONTEXT.graph

    @property
    def pool(self):
        return Context.__CONTEXT.pool

    @property
    def parent(self):
        return Context.__CONTEXT.parent

    @parent.setter
    def parent(self, value):
        Context.__CONTEXT.parent = value

    @property
    def jsonld(self):
        return {
            '@graph': self.graph,
            '@context': {}
        }

    def __init__(self):
        Context.__CONTEXT.pool = DictHashingDict()
        Context.__CONTEXT.graph = []
        Context.__CONTEXT.parent = None
        super().__init__(split=True)

    def clear(self):
        self.__init__()


ctx = Context()


class NameParserLink(AbstractLink):
    def execute(self, obj):
        return HumanName(obj)


class DateParserLink(AbstractLink):
    def execute(self, obj):
        return dateparser.parse(obj)


class ConcatLink(AbstractLink):
    def execute(self, obj):
        return '\n'.join(obj)


class ParentLink(AbstractLink):
    def execute(self, obj):
        return ctx.parent


class IteratorLink(AbstractLink):
    def __init__(self):
        super().__init__()
        self.__anchor = AnchorLink(split=False)

    def __add__(self, step):
        self.__anchor.chain()[-1] + step
        return self

    def execute(self, obj):
        if not isinstance(obj, (list, tuple)):
            obj = (obj, )
        return [self.__anchor.execute(sub) for sub in obj]


class PathLink(AbstractLink):
    def __init__(self, segment):
        self._segment = segment
        super().__init__()

    def execute(self, obj):
        if isinstance(obj, etree._Element):
            return obj.xpath('./*[local-name()=\'{}\']'.format(self._segment))
        return obj[self._segment]


class IndexLink(AbstractLink):
    def __init__(self, index):
        self._index = index
        super().__init__()

    def execute(self, obj):
        return obj[self._index]


class TextLink(AbstractLink):
    def execute(self, obj):
        return obj.text


class ParserMeta(type):

    def __new__(cls, name, bases, attrs):
        parsers = {**bases[0].parsers} if bases else {}
        for key, value in tuple(attrs.items()):
            if isinstance(value, AbstractLink):
                parsers[key] = attrs.pop(key).chain()[0]
        attrs['parsers'] = parsers

        return super(ParserMeta, cls).__new__(cls, name, bases, attrs)


class Subparser:
    def __init__(self, name, is_list=False):
        self._name = name
        self._is_list = is_list

    def resolve(self, parent, value):
        prev, ctx.parent = ctx.parent, parent.context
        klass = getattr(__import__(parent.__module__, fromlist=(self._name,)), self._name)
        if self._is_list:
            ret = [klass(v).parse() for v in value]
        else:
            ret = klass(value).parse()
        ctx.parent = prev
        return ret


class AbstractParser(metaclass=ParserMeta):
    target = None
    subparsers = {}

    def __init__(self, context):
        self.context = context
        self._value = ctx.pool.get((context, self.__class__.__name__))

    def parse(self):
        if self._value:
            return self._value

        inst = {'@id': '_:' + uuid.uuid4().hex, '@type': self.__class__.__name__}

        ctx.pool[(self.context, inst['@type'])] = inst

        inst = {**inst, **{
            key: (key in self.subparsers and self.subparsers[key].resolve(self, chain.execute(self.context))) or chain.execute(self.context)
            for key, chain in self.parsers.items()
        }}

        ctx.graph.append(inst)

        return {'@id': inst['@id'], '@type': inst['@type']}


#### Public API ####

def ParseDate(chain):
    return chain + DateParserLink()


def ParseName(chain):
    return chain + NameParserLink()


def Concat(chain):
    return chain + ConcatLink()


class AbstractOrganization(AbstractParser):
    target = share.models.Organization


class AbstractAffiliation(AbstractParser):
    target = share.models.Affiliation
    person = ctx['parent']
    subparsers = {'organization': Subparser('Organization'), 'person': Subparser('Person')}


class AbstractEmail(AbstractParser):
    target = share.models.Email


class AbstractPerson(AbstractParser):
    target = share.models.Person
    subparsers = {'affiliations': Subparser('Affiliation', is_list=True)}
    # subparsers = {'emails': Subparser('Email', is_list=True)}


class AbstractManuscript(AbstractParser):
    target = share.models.Manuscript
    subparsers = {'contributors': Subparser('Contributor', is_list=True)}


class AbstractContributor(AbstractParser):
    target = share.models.Contributor
    manuscript = ctx['parent']
    subparsers = {'person': Subparser('Person'), 'manuscript': Subparser('Manuscript')}

#### /Public API ####
