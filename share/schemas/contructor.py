import collections

from django.db import models

from share.util import TopologicalSorter


class ModelConstructor:

    def __init__(self, schema, name_tpl='{}', base=None, meta=None, module=None):
        self.base = base or models.Model
        self.name_tpl = name_tpl
        self.schema = schema
        self.meta = meta or {}
        self.module = module or __name__

        if None not in self.meta:
            self.meta[None] = {}

        self._models = None
        self._sorted_types = TopologicalSorter(
            self.schema.types.values(),
            dependencies=lambda x: [f.related for f in x.fields if f.is_relation],
            key=lambda x: x.name,
        ).sorted()

    def construct(self):
        if self._models:
            return self._models

        self._models = collections.OrderedDict()
        for typ in self._sorted_types:
            model = typ.to_django_model(self)
            self._models[typ.name] = model

        return self._models

    def meta_for(self, typ):
        return {**self.meta.get(typ.name, {}), **self.meta[None]}

    def name_for(self, typ):
        return self.name_tpl.format(typ.name)

    def __getitem__(self, name):
        if self._models is None:
            raise ValueError('Models have not been constructed yet')
        return self._models[name]

    def __iter__(self):
        if self._models is None:
            raise ValueError('Models have not been constructed yet')
        return iter(self._models.values())
