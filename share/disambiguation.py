import abc

from django.core.exceptions import ValidationError

from share import models

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


class UniqueAttrDisambiguator(Disambiguator):
    def disambiguate(self):
        if not self.attrs.get(self.unique_attr):
            return None
        try:
            query = {self.unique_attr: self.attrs[self.unique_attr]}
            return self.model.objects.get(**query)
        except self.model.DoesNotExist:
            return None


class CreativeWorkIdentifierDisambiguator(UniqueAttrDisambiguator):
    FOR_MODEL = models.CreativeWorkIdentifier
    unique_attr = 'uri'


class PersonIdentifierDisambiguator(UniqueAttrDisambiguator):
    FOR_MODEL = models.PersonIdentifier
    unique_attr = 'uri'


class TagDisambiguator(UniqueAttrDisambiguator):
    FOR_MODEL = models.Tag
    unique_attr = 'name'


class PersonDisambiguator(Disambiguator):
    FOR_MODEL = models.Person

    def disambiguate(self):
        for id in self.attrs.get('identifiers', ()):
            try:
                identifier = models.PersonIdentifier.objects.get(id=id)
                return identifier.person
            except models.PersonIdentifier.DoesNotExist:
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
                identifier = models.CreativeWorkIdentifier.objects.get(id=id)
                return identifier.creative_work
            except models.CreativeWorkIdentifier.DoesNotExist:
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
