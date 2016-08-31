import abc

from django.core.exceptions import ValidationError

from share.models import Tag
from share.models import Link
from share.models import Person
from share.models import Subject
from share.models import Contributor
from share.models import Association
from share.models import Affiliation
from share.models import PersonEmail
from share.models.meta import ThroughLinks
from share.models import AbstractCreativeWork


__all__ = ('disambiguate', )


def disambiguate(id, attrs, model):
    for cls in Disambiguator.__subclasses__():
        if getattr(cls, 'FOR_MODEL', None) == model._meta.concrete_model:
            return cls(id, attrs, model).find()

    return GenericDisambiguator(id, attrs, model).find()


class Disambiguator(metaclass=abc.ABCMeta):

    def __init__(self, id, attrs, model):
        self.id = id
        self.model = model
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

    @property
    def is_through_table(self):
        # TODO fix this...
        return 'Through' in self.model.__name__ or self.model in {
            Contributor,
            Association,
            Affiliation,
            PersonEmail,
        }

    def disambiguate(self):
        if not self.attrs:
            return None

        if self.is_through_table:
            return self._disambiguate_through()

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

    def _disambiguate_through(self):
        fields = [
            f for f in self.model._meta.get_fields()
            if f.is_relation and f.editable and f.name not in {'same_as', 'extra'}
        ]
        # Don't dissambiguate through tables that don't have both sides filled out
        for field in fields:
            if field.name not in self.attrs:
                return None

        return self.model.objects.filter(**{k: v for k, v in self.attrs.items() if not isinstance(v, list)}).first()


class LinkDisambiguator(Disambiguator):
    FOR_MODEL = Link

    def disambiguate(self):
        if not self.attrs.get('url'):
            return None
        return Link.objects.filter(url=self.attrs['url']).first()


class TagDisambiguator(Disambiguator):
    FOR_MODEL = Tag

    def disambiguate(self):
        if not self.attrs.get('name'):
            return None
        return Tag.objects.filter(name=self.attrs['name']).first()


class PersonDisambiguator(Disambiguator):
    FOR_MODEL = Person

    def disambiguate(self):
        return Person.objects.filter(
            suffix=self.attrs.get('suffix', ''),
            given_name=self.attrs.get('given_name', ''),
            family_name=self.attrs.get('family_name', ''),
            additional_name=self.attrs.get('additional_name', ''),
        ).first()


class SubjectDisambiguator(Disambiguator):
    FOR_MODEL = Subject

    def disambiguate(self):
        if not self.attrs.get('name'):
            return None
        subjects = Subject.objects.filter(name__iexact=self.attrs['name'])
        if subjects:
            return subjects.first()
        raise ValidationError('Invalid subject: {}'.format(self.attrs['name']))


class AbstractCreativeWorkDisambiguator(Disambiguator):
    FOR_MODEL = AbstractCreativeWork

    def disambiguate(self):
        if self.attrs.get('links'):
            for link in self.attrs.get('links'):
                qs = ThroughLinks.objects.filter(link=link).select_related('creative_work')
                if qs:
                    return qs.first().creative_work

        if not self.attrs.get('title') or len(self.attrs['title']) > 2048:
            return None

        self.attrs.pop('description', None)

        # Limitting the length of title forces postgres to use the partial index
        return self.model.objects.filter(**{k: v for k, v in self.attrs.items() if not isinstance(v, list)}).extra(where=('octet_length(title) < 2049', )).first()
