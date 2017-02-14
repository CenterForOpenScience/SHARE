from django.db import models
from django.contrib.postgres.fields import ArrayField, JSONField

from share import harvest
from share import process


class SourceFavicon(models.Model):
    source = models.OneToOneField('Source', on_delete=DATABASE_CASCADE)
    image = models.BinaryField()


@deconstructible
class SourceFaviconStorage(Storage):
    def _open(self, name, mode='rb'):
        assert mode == 'rb'
        favicon = SourceFavicon.objects.get(source_name=name)
        return ContentFile(favicon.image)

    def _save(self, name, content):
        source = Source.objects.get(name=name)
        SourceFavicon.objects.update_or_create(source_id=source.id, defaults={'image': content.read()})
        return name

    def delete(self, name):
        SourceFavicon.objects.get(source_name=name).delete()

    def get_available_name(self, name, max_length=None):
        return name

    def url(self, name):
        return reverse('user_favicon', kwargs={'username': name})


def favicon_name(instance, filename):
    return instance.username


class Source(models.Model):
    name = models.TextField(unique=True)
    long_title = models.TextField()
    home_page = models.URLField()
    base_url = models.URLField()
    favicon = models.ImageField(upload_to=favicon_name, storage=SourceFaviconStorage(), null=True)

    # TODO replace with Django permissions something something
    user = models.ForeignKey('ShareUser')

    harvester = models.ForeignKey('Harvester')
    harvester_args = JSONField(null=True)

    transformer = models.ForeignKey('Transformer')
    transformer_args = JSONField(null=True)

    disabled = models.BooleanField(default=False)


class Harvester(models.Model):
    key = models.TextField(unique=True)
    name = models.TextField()
    version = models.TextField()


class Transformer(models.Model):
    key = models.TextField(unique=True)
    name = models.TextField()
    version = models.TextField()
