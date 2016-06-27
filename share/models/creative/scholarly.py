from django.db import models

from share.models.creative.base import AbstractCreativeWork

__all__ = ('Preprint', 'Manuscript')

# TODO: Refactor this so there's a URLifiedMixin that adds a URL to each model

class Preprint(AbstractCreativeWork):
    posted_date = models.DateTimeField()


class Manuscript(AbstractCreativeWork):
    pass
