from django.db import models

from share.models.creative.base import CreativeWork


__all__ = ('Preprint', 'Manuscript')


class Preprint(CreativeWork):
    posted_date = models.DateTimeField()


class Manuscript(CreativeWork):
    pass
