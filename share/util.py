import re
import os
import yaml
from collections import OrderedDict


class IDObfuscator:
    NUM = 0xDEADBEEF
    MOD = 10000000000
    MOD_INV = 0x17A991C0F
    # Match HHHHH-HHH-HHH Where H is any hexidecimal digit
    ID_RE = re.compile(r'([0-9A-Fa-f]{2})([0-9A-Fa-f]{3})-([0-9A-Fa-f]{3})-([0-9A-Fa-f]{3})')

    @classmethod
    def encode(cls, instance):
        return cls.encode_id(instance.id, type(instance))

    @classmethod
    def encode_id(cls, pk, model):
        from django.contrib.contenttypes.models import ContentType

        model_id = ContentType.objects.get_for_model(model).id
        encoded = '{:09X}'.format(pk * cls.NUM % cls.MOD)
        return '{:02X}{}-{}-{}'.format(model_id, encoded[:3], encoded[3:6], encoded[6:])

    @classmethod
    def decode(cls, id):
        from django.contrib.contenttypes.models import ContentType

        match = cls.ID_RE.match(id)
        assert match, '"{}" is not a valid ID'.format(id)
        model_id, *pks = match.groups()
        return ContentType.objects.get(pk=int(model_id, 16)).model_class(), int(''.join(pks), 16) * cls.MOD_INV % cls.MOD

    @classmethod
    def decode_id(cls, id):
        return cls.decode(id)[1]

    @classmethod
    def resolve(cls, id):
        model, pk = cls.decode(id)
        return model.objects.get(pk=pk)

    @classmethod
    def resolver(cls, self, args, context, info):
        return cls.resolve(args.get('id', ''))


class CyclicalDependency(Exception):
    pass


# Sort a list of nodes topographically, so a node is always preceded by its dependencies
class TopographicalSorter:

    # `nodes`: Iterable of objects
    # `dependencies`: Callable that takes a single argument (a node) and returns an iterable of its dependent nodes (or keys, if `key` is given)
    # `key`: Callable that takes a single argument (a node) and returns a unique key. If omitted, nodes will be compared for equality directly.
    def __init__(self, nodes, dependencies, key=None):
        self.__sorted = []
        self.__nodes = list(nodes)
        self.__visited = set()
        self.__visiting = set()
        self.__dependencies = dependencies
        self.__key = key
        self.__node_map = {key(n): n for n in nodes} if key else None

    def sorted(self):
        if not self.__nodes:
            return self.__sorted

        while self.__nodes:
            n = self.__nodes.pop(0)
            self.__visit(n)

        return self.__sorted

    def __visit(self, node):
        key = self.__key(node) if self.__key else node
        if key in self.__visiting:
            raise CyclicalDependency(key, self.__visiting)

        if key in self.__visited:
            return

        self.__visiting.add(key)
        for k in self.__dependencies(node):
            if k is not None:
                self.__visit(self.__get_node(k))

        self.__visited.add(key)
        self.__sorted.append(node)
        self.__visiting.remove(key)

    def __get_node(self, key):
        return self.__node_map[key] if self.__node_map else key


# Generate subclasses from yaml specs
class ModelGenerator:
    def __init__(self, field_types={}):
        self.__field_types = field_types

    def subclasses_from_yaml(self, file_name, base):
        yaml_file = re.sub(r'\.py$', '.yaml', os.path.abspath(file_name))
        with open(yaml_file) as fobj:
            model_specs = yaml.load(fobj)

        return self.generate_subclasses(model_specs, base)

    def generate_subclasses(self, model_specs, base):
        models = {}
        for (name, mspec) in model_specs.items():
            fields = mspec.get('fields', {})
            model = type(name, (base,), {
                **{fname: self._get_field(fspec) for (fname, fspec) in fields.items()},
                '__doc__': mspec.get('description'),
                '__qualname__': name,
                '__module__': base.__module__
            })
            models[name] = model
            models[model.VersionModel.__name__] = model.VersionModel

            children = mspec.get('children')
            if children:
                models.update(self.generate_subclasses(children, model))

        return models

    def _get_field(self, field_spec):
        field_class = self.__field_types[field_spec['type']]
        return field_class(*field_spec.get('args', []), **field_spec.get('kwargs', {}))


class DictHashingDict:
    # A wrapper around dicts that can have dicts as keys

    def __init__(self):
        self.__inner = {}

    def get(self, key, *args):
        return self.__inner.get(self._hash(key), *args)

    def pop(self, key, *args):
        return self.__inner.pop(self._hash(key), *args)

    def setdefault(self, key, *args):
        return self.__inner.setdefault(self._hash(key), *args)

    def __getitem__(self, key):
        return self.__inner[self._hash(key)]

    def __setitem__(self, key, value):
        self.__inner[self._hash(key)] = value

    def __contains__(self, key):
        return self._hash(key) in self.__inner

    def _hash(self, val):
        if isinstance(val, dict):
            if not isinstance(val, OrderedDict):
                val = tuple((k, self._hash(v)) for k, v in sorted(val.items(), key=lambda x: x[0]))
            else:
                val = tuple((k, self._hash(v)) for k, v in val.items())
        if isinstance(val, (list, tuple)):
            val = tuple(self._hash(v) for v in val)
        return val
