from functools import reduce


def ParseName(chain):
    return chain + NameParser()


class NameParser:
    pass


class InferredPath:
    def __init__(self, segment):
        self._segment = segment

    def execute(self, obj):
        if isinstance(obj, dict):
            return obj[self._segment]
        raise ValueError('Unable to parse path "{}" out of {}'.format(self._segment, obj))


class CommandChain:

    def __init__(self, steps):
        self._steps = tuple(steps)

    def __add__(self, step):
        return CommandChain(self._steps + (step,))

    def __getitem__(self, name):
        raise Exception

    def __call__(self, name):
        return self + InferredPath(name)

    def __getattr__(self, name):
        return self + InferredPath(name)

    def execute(self, obj):
        return reduce(lambda acc, cur: cur.execute(acc), self._steps)


ctx = CommandChain([])


class ParserMeta(type):

    def __new__(cls, name, bases, attrs):
        parsers = {}
        for key, value in tuple(attrs.items()):
            if isinstance(value, CommandChain):
                parsers[key] = attrs.pop(key)
        attrs['parsers'] = parsers

        return super(ParserMeta, cls).__new__(cls, name, bases, attrs)


class AbstractParser(metaclass=ParserMeta):
    target = None

    def parse(self, obj):
        return self.target(**{
            key: chain.execute(obj)
            for key, chain in self.parsers
        })


class AbstractPerson(AbstractParser):
    pass
