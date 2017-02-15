from django.contrib.postgres.fields import ArrayField, JSONField
from django.core.files.storage import Storage
from django.db import models
from django.utils.deconstruct import deconstructible

from db.deletion import DATABASE_CASCADE

from share import harvest
from share import process


class SourceIcon(models.Model):
    source = models.OneToOneField('Source', on_delete=DATABASE_CASCADE)
    image = models.BinaryField()


@deconstructible
class SourceIconStorage(Storage):
    def _open(self, name, mode='rb'):
        assert mode == 'rb'
        icon = SourceIcon.objects.get(source_name=name)
        return ContentFile(icon.image)

    def _save(self, name, content):
        source = Source.objects.get(name=name)
        SourceIcon.objects.update_or_create(source_id=source.id, defaults={'image': content.read()})
        return name

    def delete(self, name):
        SourceIcon.objects.get(source_name=name).delete()

    def get_available_name(self, name, max_length=None):
        return name

    def url(self, name):
        return reverse('source_icon', kwargs={'source_name': name})


def icon_name(instance, filename):
    return instance.name


class NaturalKeyManager(FuzzyCountManager):
    def __init__(self, key_field):
        self.key_field = key_field

    def get_by_natural_key(self, key):
        return self.get(**{self.key_field: key})


class Source(models.Model):
    name = models.TextField(unique=True)
    long_title = models.TextField()
    home_page = models.URLField()
    icon = models.ImageField(upload_to=icon_name, storage=SourceIconStorage(), null=True)

    # TODO replace with Django permissions something something
    user = models.ForeignKey('ShareUser')

    objects = NaturalKeyManager('name')

    def natural_key(self):
        return self.name


class SourceHarvester(models.Model):
    source = models.ForeignKey('Source')
    base_url = models.URLField()
    earliest_date = models.DateField(null=True)

    harvester = models.ForeignKey('Harvester')
    harvester_kwargs = JSONField(null=True)

    transformer = models.ForeignKey('Transformer')
    transformer_kwargs = JSONField(null=True)

    disabled = models.BooleanField(default=False)


class Harvester(models.Model):
    key = models.TextField(unique=True)
    date_created = models.DateTimeField(auto_now_add=True)

    objects = NaturalKeyManager('key')

    def natural_key(self):
        return self.key


class Transformer(models.Model):
    key = models.TextField(unique=True)
    date_created = models.DateTimeField(auto_now_add=True)

    objects = NaturalKeyManager('key')

    def natural_key(self):
        return self.key
