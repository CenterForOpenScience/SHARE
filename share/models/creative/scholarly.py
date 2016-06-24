from django.db import models

from share.models.creative.base import AbstractCreativeWork


__all__ = ('Preprint', 'Manuscript')


class Preprint(AbstractCreativeWork):
    posted_date = models.DateTimeField()


class Manuscript(AbstractCreativeWork):
    pass
