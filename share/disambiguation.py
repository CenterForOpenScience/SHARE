import abc

from django.core.exceptions import ValidationError

from share.models import Tag
from share.models import Link
from share.models import Person
from share.models import Subject


__all__ = ('disambiguate', )


def disambiguate(id, attrs, model):
    for cls in Disambiguator.__subclasses__():
        if getattr(cls, 'FOR_MODEL', None) == model:
            return cls(id, attrs).find()

    return GenericDisambiguator(id, attrs, model).find()


class Disambiguator(metaclass=abc.ABCMeta):

    def __init__(self, id, attrs):
        self.id = id
        # only include attrs with truthy values
        self.attrs = {k: v for k, v in attrs.items() if v}
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
        self.attrs.pop('description', None)
        if len(self.attrs.get('title', '')) > 2048:
            return None
        elif self.attrs.get('title', None):
            # if the model has a title, it's an abstractcreativework
            # limit the query so it uses an index
            return self.model.objects.filter(**self.attrs).extra(
                where=[
                    "octet_length(title) < 2049"
                ]
            ).first()
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


class SubjectDisambiguator(Disambiguator):
    model = Subject
    FOR_MODEL = Subject

    def disambiguate(self):
        if not self.attrs.get('name'):
            return None
        subjects = Subject.objects.filter(name__iexact=self.attrs['name'])
        if subjects:
            return subjects.first()
        subjects = Subject.objects.filter(synonyms__synonym__iexact=self.attrs['name'])
        if subjects:
            # TODO allow mapping a synonym to multiple subjects?
            return synonyms.first()
        raise ValidationError('Invalid subject: {}'.format(self.attrs['name']))
