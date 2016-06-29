import threading
from functools import reduce
from collections import deque

import dateparser

from lxml import etree

from nameparser import HumanName


__all__ = ('ParseDate', 'ParseName', 'Trim', 'Concat')


#### Public API ####

def ParseDate(chain):
    return chain + DateParserLink()


def ParseName(chain):
    return chain + NameParserLink()


def Trim(chain):
    return chain + TrimLink()


def Concat(chain):
    return AbstractLink.__add__(chain, ConcatLink())

### /Public API


# A wrapper around dicts that can have dicts as keys
class DictHashingDict:

    def __init__(self):
        self.__inner = {}

    def get(self, key, *args):
        return self.__inner.get(self._hash(key), *args)

    def __getitem__(self, key):
        return self.__inner[self._hash(key)]

    def __setitem__(self, key, value):
        self.__inner[self._hash(key)] = value

    def _hash(self, val):
        if isinstance(val, dict):
            val = tuple((k, self._hash(v)) for k, v in val.items())
        if isinstance(val, (list, tuple)):
            val = tuple(self._hash(v) for v in val)
        return val


# BaseClass for all links
# Links are a single step of the parsing process
# Links may not mutate the object passed into them
# A chain is any number of links added together
class AbstractLink:

    def __init__(self, _next=None, _prev=None):
        # next and prev are generally set by the __add__ method
        self._next = _next
        self._prev = _prev

    # Build the entire chain this link is a part of
    # NOTE: This results in the entire chain rather than starting from the current link
    def chain(self):
        first = self
        while first._prev:
            first = first._prev
        deq = deque([first])
        while deq[-1]._next:
            deq.append(deq[-1]._next)
        return tuple(deq)

    # Transformation logic goes here
    def execute(self, obj):
        raise NotImplemented

    # Short cut method(s) for specific tranforms
    def text(self):
        return self + TextLink()

    def xpath(self, xpath):
        return self + XPathLink(xpath)

    # Add a link into an existing chain
    def __add__(self, step):
        self._next = step
        step._prev = self
        return step

    # Reserved for special cases
    # Any other use is an error
    def __getitem__(self, name):
        if name == '*':
            return self + IteratorLink()
        if name == 'parent':
            return self + ParentLink()
        if isinstance(name, int):
            return self + IndexLink(name)
        raise Exception

    # For handling paths that are not valid python
    # or are already used. IE text, execute, oai:title
    # ctx('oai:title')
    def __call__(self, name):
        return self + PathLink(name)

    # The preferred way of building paths.
    # Can express either json paths or xpaths
    # ctx.root.nextelement[0].first_item_attribute
    def __getattr__(self, name):
        return self + PathLink(name)


# The begining link for all chains
# Contains logic for executing a chain against an object
# Adding another link to an anchor will result in a copy of the
# original anchor
class AnchorLink(AbstractLink):

    def execute(self, obj):
        return reduce(lambda acc, cur: cur.execute(acc), self.chain()[1:], obj)


class Context(AnchorLink):

    __CONTEXT = threading.local()

    @property
    def jsonld(self):
        return {
            '@graph': self.graph,
            '@context': {}
        }

    def __init__(self):
        super().__init__()

        if hasattr(Context.__CONTEXT, '_ctxdict'):
            self.__dict__ = Context.__CONTEXT._ctxdict
            return

        Context.__CONTEXT._ctxdict = self.__dict__
        self.clear()

    def clear(self):
        self.graph = []
        self.parent = None
        self.pool = DictHashingDict()

    def __add__(self, step):
        return AnchorLink() + step


class NameParserLink(AbstractLink):
    def execute(self, obj):
        return HumanName(obj)


class DateParserLink(AbstractLink):
    def execute(self, obj):
        return dateparser.parse(obj)


class ConcatLink(AbstractLink):
    def execute(self, obj):
        return '\n'.join(obj)


class TrimLink(AbstractLink):
    def execute(self, obj):
        return obj.strip()


class ParentLink(AbstractLink):
    def execute(self, obj):
        return Context().parent


class IteratorLink(AbstractLink):
    def __init__(self):
        super().__init__()
        self.__anchor = AnchorLink()

    def __add__(self, step):
        # Attach all new links to the "subchain"
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
            # Dirty hack to avoid namespaces with xpath
            # Anything name "<namespace>:<node>" will be accessed as <node>
            # IE: oai:title -> title
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


class XPathLink(AbstractLink):
    def __init__(self, xpath):
        self._xpath = xpath
        super().__init__()

    def execute(self, obj):
        return obj.xpath(self._xpath)

