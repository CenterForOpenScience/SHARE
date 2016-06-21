import abc


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
        try:
            self.model.objects.get(**self.attrs)
        except self.model.DoesNotExist:
            return None
