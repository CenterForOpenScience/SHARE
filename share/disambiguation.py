import abc

from django.core.exceptions import ValidationError

from share import models
from share.models.people import PersonIdentifier
from share.models.meta import WorkIdentifier


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
            models.Contributor,
            models.Association,
            models.Affiliation,
            models.PersonEmail,
        }

    def disambiguate(self):
        if not self.attrs:
            return None

        if self.is_through_table:
            return self._disambiguate_through()

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

        try:
            return self.model.objects.get(**{field.name: self.attrs[field.name] for field in fields})
        except (self.model.DoesNotExist, self.model.MultipleObjectsReturned):
            return None


class IdentifierDisambiguator(Disambiguator):
    FOR_MODEL = models.Identifier

    def disambiguate(self):
        if not self.attrs.get('url'):
            return None
        try:
            return self.model.objects.get(url=self.attrs['url'])
        except self.model.DoesNotExist:
            return None


class TagDisambiguator(Disambiguator):
    FOR_MODEL = models.Tag

    def disambiguate(self):
        if not self.attrs.get('name'):
            return None
        try:
            return models.Tag.objects.get(name=self.attrs['name'])
        except models.Tag.DoesNotExist:
            return None


class PersonDisambiguator(Disambiguator):
    FOR_MODEL = models.Person

    def disambiguate(self):
        for id in self.attrs.get('identifiers', ()):
            try:
                person_identifier = PersonIdentifier.objects.get(identifier=id)
                return person_identifier.person
            except PersonIdentifier.DoesNotExist:
                pass
        return None


class SubjectDisambiguator(Disambiguator):
    FOR_MODEL = models.Subject

    def disambiguate(self):
        if not self.attrs.get('name'):
            return None
        try:
            return models.Subject.objects.get(name=self.attrs['name'])
        except models.Subject.DoesNotExist:
            raise ValidationError('Invalid subject: {}'.format(self.attrs['name']))


class AbstractCreativeWorkDisambiguator(Disambiguator):
    FOR_MODEL = models.AbstractCreativeWork

    def disambiguate(self):
        for id in self.attrs.get('identifiers', ()):
            try:
                work_identifier = WorkIdentifier.objects.get(identifier=id)
                return work_identifier.creative_work
            except WorkIdentifier.DoesNotExist:
                pass
        return None


class RelationDisambiguator(Disambiguator):
    FOR_MODEL = models.Relation

    def disambiguate(self):
        filters = {
            'from_work': self.attrs.get('from_work'),
            'to_work': self.attrs.get('to_work')
        }
        relation_type = self.attrs.get('relation_type')
        if relation_type != models.Relation.RELATION_TYPES.unknown:
            filters['relation_type'] = relation_type
        try:
            return models.Relation.objects.filter(**filters)[0]
        except IndexError:
            return None
