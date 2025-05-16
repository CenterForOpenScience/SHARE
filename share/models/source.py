from django.db import models

from share.util import BaseJSONAPIMeta


__all__ = ('Source', 'SourceManager',)


class SourceManager(models.Manager):
    use_in_migrations = True

    def get_by_natural_key(self, key):
        return self.get(name=key)


class Source(models.Model):
    name = models.TextField(unique=True)
    long_title = models.TextField(unique=True)
    home_page = models.URLField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    # Whether or not this SourceConfig collects original content
    # If True changes made by this source cannot be overwritten
    # This should probably be on SourceConfig but placing it on Source
    # is much easier for the moment.
    # I also haven't seen a situation where a Source has two feeds that we harvest
    # where one provider unreliable metadata but the other does not.
    canonical = models.BooleanField(default=False, db_index=True)

    # TODO replace with object permissions, allow multiple sources per user (SHARE-996)
    user = models.OneToOneField('ShareUser', null=True, on_delete=models.CASCADE)

    objects = SourceManager()

    class JSONAPIMeta(BaseJSONAPIMeta):
        pass

    def natural_key(self):
        return (self.name,)

    def __repr__(self):
        return '<{}({}, {}, {})>'.format(self.__class__.__name__, self.pk, self.name, self.long_title)

    def __str__(self):
        return repr(self)
