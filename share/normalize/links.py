from collections import deque
from functools import reduce
import json
import logging
import re
import threading

import xmltodict

import arrow

from lxml import etree

from pycountry import languages

from nameparser import HumanName

logger = logging.getLogger(__name__)


__all__ = ('ParseDate', 'ParseName', 'ParseLanguage', 'Trim', 'Concat', 'Map', 'Delegate', 'Maybe', 'XPath', 'Join', 'RunPython', 'Static', 'Try', 'Subjects', 'OneOf', 'Orcid', 'DOI')


#### Public API ####

def ParseDate(chain):
    return chain + DateParserLink()


def ParseName(chain):
    return chain + NameParserLink()


def ParseLanguage(chain):
    return chain + LanguageParserLink()


def Trim(chain):
    return chain + TrimLink()


def Concat(*chains, deep=False):
    return AnchorLink() + ConcatLink(*chains, deep=deep)


def XPath(chain, path):
    return chain + XPathLink(path)


def Join(chain, joiner='\n'):
    return chain + JoinLink(joiner=joiner)


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


def Subjects(*chains):
    return Concat(Map(MapSubjectLink(), *chains), deep=True)


def OneOf(*chains):
    return OneOfLink(*chains)


def Orcid(chain=None):
    if chain:
        return chain + OrcidLink()
    return OrcidLink()


def DOI(chain=None):
    if chain:
        return chain + DOILink()
    return DOILink()

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
        try:
            return self.execute(obj)
        finally:
            Context().frames.pop(-1)


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
        if isinstance(maybe_code, dict):
            maybe_code = maybe_code['#text']
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
    def __init__(self, *chains, deep=False):
        self._chains = chains
        self._deep = deep
        super().__init__()

    def _concat(self, acc, val):
        if val is None:
            return acc
        if not isinstance(val, list):
            val = [val]
        elif self._deep:
            val = reduce(self._concat, val, [])
        return acc + [v for v in val if v != '' and v is not None]

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
        chain = list(step.chain())
        while isinstance(chain[0], AnchorLink):
            chain.pop(0)

        self.__anchor.chain()[-1] + chain[0]
        return self

    def execute(self, obj):
        if not isinstance(obj, (list, tuple)):
            obj = (obj, )
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


class MapSubjectLink(AbstractLink):

    with open('synonyms.json') as fobj:
        MAPPING = json.load(fobj)

    def execute(self, obj):
        if not obj:
            return None

        if isinstance(obj, list):
            return [self.execute(x) for x in obj]

        assert isinstance(obj, str), 'Subjects must be strings. Got {}.'.format(type(obj))

        mapped = self.MAPPING.get(obj.lower())

        if not mapped:
            logger.warning('No synonyms found for term "%s"', obj)

        return mapped


class OneOfLink(AbstractLink):

    def __init__(self, *chains):
        self._chains = chains
        super().__init__()

    def execute(self, obj):
        errors = []
        for chain in self._chains:
            try:
                return chain.chain()[0].run(obj)
            except Exception as e:
                errors.append(e)

        raise Exception('All chains failed {}'.format(errors))


class OrcidLink(AbstractLink):
    """Reformat Orcids to the cannonical form
    https://orcid.org/xxx-xxxx-xxxx-xxxx

    0000000248692419
    0000-0002-4869-2419
    https://orcid.org/0000-0002-4869-2419

    Any of the above would be transformed into https://orcid.org/0000-0002-4869-2419
    """

    ORCID_URL = 'https://orcid.org/'
    ORCID_RE = re.compile(r'(\d{4})-?(\d{4})-?(\d{4})-?(\d{3}(?:\d|X))')

    def checksum(self, digits):
        # ORCID Checksum  http://support.orcid.org/knowledgebase/articles/116780-structure-of-the-orcid-identifier
        total, checksum = 0, digits[-1]
        for digit in digits[:-1]:
            total = (total + int(digit, 36)) * 2
        check = (12 - (total % 11)) % 11
        if check == 10:
            check = 'X'
        if str(check) != checksum:
            raise ValueError('{} is not a valid ORCID. Failed checksum'.format(digits))

    def execute(self, obj):
        if not isinstance(obj, str):
            raise TypeError('{} is not of type str'.format(obj))
        match = re.search(self.ORCID_RE, obj)
        if not match:
            raise ValueError('{} cannot be expressed as an orcid'.format(obj))
        self.checksum(''.join(match.groups()))
        return '{}{}-{}-{}-{}'.format(self.ORCID_URL, *match.groups())


class DOILink(AbstractLink):
    """Reformt DOIs to the cannonical form

    * All DOIs will be valid URIs
    * All DOIs will use https
    * All DOI paths will be uppercased

    Reference:
        https://www.doi.org/doi_handbook/2_Numbering.html
        https://stackoverflow.com/questions/27910/finding-a-doi-in-a-document-or-page
    """
    DOI_URL = 'http://dx.doi.org/'
    DOI_RE = r'\b(10\.\d{4,}(?:\.\d+)*/\S+(?:(?!["&\'<>])\S))\b'

    def execute(self, obj):
        if not isinstance(obj, str):
            raise TypeError('{} is not of type str'.format(obj))
        match = re.search(self.DOI_RE, obj.upper())
        if not match:
            raise ValueError('{} is not a valid DOI'.format(obj))
        return '{}{}'.format(self.DOI_URL, *match.groups())
