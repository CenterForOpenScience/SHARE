from django.db import models

from share.models.base import ShareObject
from share.models.contributor import Person
from share.models.fields import ShareForeignKey
from share.models.creative.base import AbstractCreativeWork


class Contributor(ShareObject):
    person = ShareForeignKey(Person)
    creative_work = ShareForeignKey(AbstractCreativeWork)
    url = models.URLField(blank=True)
