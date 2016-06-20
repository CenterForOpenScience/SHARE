def Disambiguator(id, attrs, model):
    klass = None
    for sub in _Disambiguator.__subclasses__():
        if getattr(sub, 'FOR_MODEL', None) == model:
            klass = sub
            break
    else:
        klass = _Disambiguator

    return klass(id, attrs, model)


class _Disambiguator:

    def __init__(self, id, attrs, model):
        self.id = id
        self.attrs = attrs
        self.model = model
        self.is_blank = isinstance(id, str) and id.startswith('_:')

    def find(self):
        if self.id and not self.is_blank:
            return self.model.objects.get(pk=self.id)
        return self.disambiguate()

    def disambiguate(self):
        try:
            self.model.objects.get(**self.attrs)
        except self.model.DoesNotExist:
            return None
