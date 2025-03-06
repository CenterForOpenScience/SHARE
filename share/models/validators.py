from django.utils.deconstruct import deconstructible


@deconstructible
class JSONLDValidator:
    def __call__(self, *args, **kwargs):
        raise Exception('Deprecated; stop doing sharev2 stuff')
