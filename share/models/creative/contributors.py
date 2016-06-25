from django.db import models

from share.models import Person, AbstractCreativeWork
from share.models.base import ShareObject
from share.models.fields import ShareForeignKey


class Contributor(ShareObject):
    person = ShareForeignKey(Person)
    creative_work = ShareForeignKey(AbstractCreativeWork)
    url = models.URLField(blank=True)
