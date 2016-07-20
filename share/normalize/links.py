import threading
from functools import reduce
from collections import deque
import logging

import xmltodict

import arrow

from lxml import etree

from pycountry import languages

from nameparser import HumanName


logger = logging.getLogger(__name__)


__all__ = ('ParseDate', 'ParseName', 'ParseLanguage', 'Trim', 'Concat', 'Map', 'Delegate', 'Maybe', 'XPath', 'Join', 'RunPython', 'Static', 'Try')


#### Public API ####

def ParseDate(chain):
    return chain + DateParserLink()


def ParseName(chain):
    return chain + NameParserLink()


def ParseLanguage(chain):
    return chain + LanguageParserLink()


def Trim(chain):
    return chain + TrimLink()


def Concat(*chains):
    return AnchorLink() + ConcatLink(*chains)


def XPath(chain, path):
    return chain + XPathLink(path)


def Join(chain, joiner='\n'):
    return AbstractLink.__add__(chain, JoinLink(joiner=joiner))


def Maybe(chain, segment, default=None):
    return chain + MaybeLink(segment, default=default)


def Try(chain, default=None):
    return TryLink(chain, default=default)


def Map(chain, *chains):
    return Concat(*chains) + IteratorLink() + chain


def Delegate(parser, chain=None):
    if chain:
        return chain + DelegateLink(parser)
    return DelegateLink(parser)


def RunPython(function_name, chain=None, *args, **kwargs):
    if chain:
        return chain + RunPythonLink(function_name, *args, **kwargs)
    return RunPythonLink(function_name, *args, **kwargs)


def Static(value):
    return StaticLink(value)


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

    def __contains__(self, key):
        return self._hash(key) in self.__inner

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

    # Add a link into an existing chain
    def __add__(self, step):
        self._next = step
        step._prev = self
        return step

    def __radd__(self, other):
        return self + PrependLink(other)

    # For handling paths that are not valid python
    # or are already used. IE text, execute, oai:title
    # ctx('oai:title')
    def __getitem__(self, name):
        if isinstance(name, int):
            return self + IndexLink(name)
        if isinstance(name, str):
            return self + PathLink(name)
        raise Exception(
            '__getitem__ only accepts integers and strings\n'
            'Found {}'.format(name)
        )
        # raise Exception

    # Reserved for special cases
    # Any other use is an error
    def __call__(self, name):
        if name == '*':
            return self + IteratorLink()
        if name == 'parent':
            return self + ParentLink()
        if name == 'index':
            return self + GetIndexLink()
        raise Exception(
            '"{}" is not a action that __call__ can resolve\n'
            '__call__ is reserved for special actions\n'
            'If you are trying to access an element use dictionary notation'.format(name)
        )

    # The preferred way of building paths.
    # Can express either json paths or xpaths
    # ctx.root.nextelement[0].first_item_attribute
    def __getattr__(self, name):
        if name[0] == '_':
            raise Exception(
                '{} has no attribute {}\n'
                'NOTE: "_"s are reserved for accessing private attributes\n'
                'Use dictionary notation to access elements beginning with "_"s\n'.format(self, name)
            )
        return self + PathLink(name)

    def __repr__(self):
        return '<{}()>'.format(self.__class__.__name__)

    def run(self, obj):
        Context().frames.append({'link': self, 'context': obj})
        ret = self.execute(obj)
        Context().frames.pop(-1)
        return ret


# The begining link for all chains
# Contains logic for executing a chain against an object
# Adding another link to an anchor will result in a copy of the
# original anchor
class AnchorLink(AbstractLink):

    def execute(self, obj):
        return reduce(lambda acc, cur: cur.run(acc), self.chain()[1:], obj)


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
        self.frames = []
        self.parser = None
        self._config = None
        self.pool = DictHashingDict()

    def __add__(self, step):
        return AnchorLink() + step


class NameParserLink(AbstractLink):
    def execute(self, obj):
        return HumanName(obj)


class DateParserLink(AbstractLink):
    def execute(self, obj):
        if obj:
            return arrow.get(obj).to('UTC').isoformat()
        return None


class LanguageParserLink(AbstractLink):
    def execute(self, maybe_code):
        # Force indices to populate
        if not languages._is_loaded:
            languages._load()

        for kwarg in languages.indices.keys():
            try:
                return languages.get(**{kwarg: maybe_code}).iso639_3_code
            except KeyError:
                continue
        return None


class ConcatLink(AbstractLink):
    def __init__(self, *chains):
        self._chains = chains
        super().__init__()

    def _concat(self, acc, val):
        if val is None:
            return acc
        if not isinstance(val, list):
            val = [val]
        return acc + [v for v in val if v is not None]

    def execute(self, obj):
        return reduce(self._concat, [
            chain.chain()[0].run(obj)
            for chain in self._chains
        ], [])


class JoinLink(AbstractLink):
    def __init__(self, joiner='\n'):
        self._joiner = joiner
        super().__init__()

    def execute(self, obj):
        obj = obj or []
        if not isinstance(obj, (list, tuple)):
            obj = (obj, )
        return self._joiner.join(x for x in obj if x)


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
        if None in obj:
            import ipdb; ipdb.set_trace()
        return [self.__anchor.run(sub) for sub in obj]


class MaybeLink(AbstractLink):
    def __init__(self, segment, default=None):
        super().__init__()
        self._segment = segment
        self._default = default
        self.__anchor = AnchorLink()

    def __add__(self, step):
        # Attach all new links to the "subchain"
        self.__anchor.chain()[-1] + step
        return self

    def execute(self, obj):
        if not obj:
            return []
        val = obj.get(self._segment)
        if val:
            return self.__anchor.run(val)
        if len(Context().frames) > 1 and isinstance(Context().frames[-2]['link'], (IndexLink, IteratorLink, ConcatLink, JoinLink)):
            return []
        return self._default


class TryLink(AbstractLink):
    def __init__(self, chain, default=None):
        super().__init__()
        self._chain = chain
        self._default = default
        self.__anchor = AnchorLink()

    def __add__(self, step):
        # Attach all new links to the "subchain"
        self.__anchor.chain()[-1] + step
        return self

    def execute(self, obj):
        try:
            val = self._chain.chain()[0].run(obj)
        except (IndexError, KeyError):
            return self._default
        except TypeError as err:
            logger.warning('TypeError: {}. When trying to access {}'.format(err, self._chain))
            return self._default
        return self.__anchor.run(val)


class PathLink(AbstractLink):
    def __init__(self, segment):
        self._segment = segment
        super().__init__()

    def execute(self, obj):
        return obj[self._segment]

    def __repr__(self):
        return '<{}({!r})>'.format(self.__class__.__name__, self._segment)


class IndexLink(AbstractLink):
    def __init__(self, index):
        self._index = index
        super().__init__()

    def execute(self, obj):
        return obj[self._index]

    def __repr__(self):
        return '<{}([{}])>'.format(self.__class__.__name__, self._index)


class GetIndexLink(AbstractLink):
    def execute(self, obj):
        for frame in Context().frames[::-1]:
            if isinstance(frame['link'], IteratorLink):
                return frame['context'].index(obj)
        return -1
        # return Context().parent.index(obj)


class PrependLink(AbstractLink):
    def __init__(self, string):
        self._string = string
        super().__init__()

    def execute(self, obj):
        return self._string + obj


class XPathLink(AbstractLink):
    def __init__(self, xpath):
        self._xpath = xpath
        super().__init__()

    def execute(self, obj):
        unparsed_obj = xmltodict.unparse(obj)
        xml_obj = etree.XML(unparsed_obj.encode())
        elem = xml_obj.xpath(self._xpath)
        elems = [xmltodict.parse(etree.tostring(x)) for x in elem]
        if len(elems) == 1 and not isinstance(self._next, (IndexLink, IteratorLink)):
            return elems[0]
        return elems


class DelegateLink(AbstractLink):
    def __init__(self, parser):
        self._parser = parser
        super().__init__()

    def execute(self, obj):
        return self._parser(obj).parse()


class RunPythonLink(AbstractLink):
    def __init__(self, function_name, *args, **kwargs):
        self._function_name = function_name
        self._args = args
        self._kwargs = kwargs
        super().__init__()

    def execute(self, obj):
        if callable(self._function_name):
            return self._function_name(obj, *self._args, **self._kwargs)
        return getattr(Context().parser, self._function_name)(obj, *self._args, **self._kwargs)


class StaticLink(AbstractLink):
    def __init__(self, value):
        self._value = value
        super().__init__()

    def execute(self, obj):
        return self._value
