import abc

from django.core.exceptions import ValidationError

from share.models import Tag, Person, Subject, Contributor, Association, Affiliation, PersonEmail, AbstractCreativeWork, Identifier, Relation, RelationType


__all__ = ('disambiguate', )


def disambiguate(id, attrs, model):
    for cls in all_subclasses(Disambiguator):
        if getattr(cls, 'FOR_MODEL', None) == model._meta.concrete_model:
            return cls(id, attrs, model).find()

    return GenericDisambiguator(id, attrs, model).find()


def all_subclasses(cls, subclasses=None):
    if subclasses is None:
        subclasses = set()
    for subclass in cls.__subclasses__():
        subclasses.add(subclass)
        all_subclasses(subclass, subclasses)
    return subclasses


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

        try:
            return self.model.objects.get(**{field.name: self.attrs[field.name] for field in fields})
        except (self.model.DoesNotExist, self.model.MultipleObjectsReturned):
            return None


class IdentifierDisambiguator(Disambiguator):
    FOR_MODEL = Identifier

    def disambiguate(self):
        if not self.attrs.get('url'):
            return None
        try:
            return self.model.objects.get(url=self.attrs['url'])
        except self.model.DoesNotExist:
            return None


class TagDisambiguator(Disambiguator):
    FOR_MODEL = Tag

    def disambiguate(self):
        if not self.attrs.get('name'):
            return None
        try:
            return Tag.objects.get(name=self.attrs['name'])
        except Tag.DoesNotExist:
            return None


class PersonDisambiguator(Disambiguator):
    FOR_MODEL = Person

    def disambiguate(self):
        # TODO disambiguate on identifiers (only?)
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
        try:
            return Subject.objects.get(name=self.attrs['name'])
        except Subject.DoesNotExist:
            raise ValidationError('Invalid subject: {}'.format(self.attrs['name']))


class AbstractCreativeWorkDisambiguator(Disambiguator):
    FOR_MODEL = AbstractCreativeWork
    # self.model could be a subclass of AbstractCreativeWork

    def disambiguate(self):
        if self.attrs.get('identifiers'):
            for id in self.attrs.get('identifiers'):
                try:
                    identifier = Identifier.objects.select_related('creative_work').get(id=id)
                    return identifier.creative_work
                except WorkIdentifier.DoesNotExist:
                    pass
        return None


class RelationDisambiguator(Disambiguator):
    FOR_MODEL = Relation

    def disambiguate(self):
        filters = {
            'subject_work': self.attrs.get('subject_work'),
            'object_work': self.attrs.get('object_work')
        }
        if self.attrs.get('relation_type'):
            relation_type = RelationType.objects.get_by_natural_key(self.attrs.get('relation_type'))
            filters['relation_type'] = relation_type
        return Relation.objects.filter(**filters).first()
