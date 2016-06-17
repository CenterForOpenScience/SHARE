import uuid
import threading
from functools import reduce
from collections import deque

from lxml import etree

from nameparser import HumanName

import share.models


__all__ = (
    'ctx',
    'ParseName',
    'AbstractPerson',
    'AbstractEmail',
    'AbstractPreprint',
    'AbstractContributor',
)


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
    def jsonld(self):
        return {
            '@graph': self.graph,
            '@context': {}
        }

    def __init__(self):
        Context.__CONTEXT.graph = []
        super().__init__(split=True)

    def clear(self):
        Context.__CONTEXT.graph = []


ctx = Context()


class NameParserLink(AbstractLink):
    def execute(self, obj):
        return HumanName(obj)


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
        parsers = {}
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
        klass = getattr(__import__(parent.__module__, fromlist=(self._name,)), self._name)
        if self._is_list:
            return [klass(v).parse() for v in value]
        return klass(value).parse()


#### Public API ####

def ParseName(chain):
    return chain + NameParserLink()


class AbstractParser(metaclass=ParserMeta):
    target = None
    subparsers = {}

    def __init__(self, context):
        self.context = context

    def parse(self):
        inst = {
            key: (key in self.subparsers and self.subparsers[key].resolve(self, chain.execute(self.context))) or chain.execute(self.context)
            for key, chain in self.parsers.items()
        }

        inst['@type'] = self.__class__.__name__
        inst['@id'] = '_:' + uuid.uuid4().hex
        ctx.graph.append(inst)

        return {'@id': inst['@id'], '@type': inst['@type']}


class AbstractEmail(AbstractParser):
    pass


class AbstractPerson(AbstractParser):
    subparsers = {'emails': Subparser('Email', is_list=True)}


class AbstractPreprint(AbstractParser):
    subparsers = {'contributors': Subparser('Contributor', is_list=True)}


class AbstractContributor(AbstractParser):
    subparsers = {'person': Subparser('Person')}

#### /Public API ####
