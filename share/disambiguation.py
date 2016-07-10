import abc

from share.models import Tag
from share.models import Link
from share.models import Person


__all__ = ('disambiguate', )


def disambiguate(id, attrs, model):
    for cls in Disambiguator.__subclasses__():
        if getattr(cls, 'FOR_MODEL', None) == model:
            return cls(id, attrs).find()

    return GenericDisambiguator(id, attrs, model).find()


class Disambiguator(metaclass=abc.ABCMeta):

    def __init__(self, id, attrs):
        self.id = id
        self.attrs = attrs
        self.is_blank = isinstance(id, str) and id.startswith('_:')

    @abc.abstractmethod
    def disambiguate(self):
        raise NotImplementedError

    def find(self):
        if self.id and not self.is_blank:
            return self.model.objects.get(pk=self.id)
        return self.disambiguate()


class GenericDisambiguator(Disambiguator):

    def __init__(self, id, attrs, model):
        self.model = model
        super().__init__(id, attrs)

    def disambiguate(self):
        if not self.attrs:
            return None
        if len(self.attrs.get('title','')) > 2048:
            return None
        self.attrs.pop('description', None)
        return self.model.objects.filter(**self.attrs).first()


class LinkDisambiguator(Disambiguator):
    model = Link
    FOR_MODEL = Link

    def disambiguate(self):
        if not self.attrs.get('url'):
            return None
        return Link.objects.filter(url=self.attrs['url']).first()


class TagDisambiguator(Disambiguator):
    model = Tag
    FOR_MODEL = Tag

    def disambiguate(self):
        if not self.attrs.get('name'):
            return None
        return Tag.objects.filter(name=self.attrs['name']).first()


class PersonDisambiguator(Disambiguator):
    model = Person
    FOR_MODEL = Person

    def disambiguate(self):
        return Person.objects.filter(
            suffix=self.attrs.get('suffix'),
            given_name=self.attrs.get('given_name'),
            family_name=self.attrs.get('family_name'),
            additional_name=self.attrs.get('additional_name'),
        ).first()
