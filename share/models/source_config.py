from __future__ import annotations

from django.db import models

from share.models.core import ShareUser
from share.models.source import Source
from share.util import BaseJSONAPIMeta


__all__ = ('SourceConfig',)


class SourceConfigManager(models.Manager['SourceConfig']):
    use_in_migrations = True

    def get_by_natural_key(self, key) -> SourceConfig:
        return self.get(label=key)

    def get_or_create_push_config(self, user, transformer_key=None) -> SourceConfig:
        assert isinstance(user, ShareUser)
        _config_label = '.'.join((
            user.username,
            transformer_key or 'rdf',  # TODO: something cleaner?
        ))
        try:
            _config = SourceConfig.objects.get(label=_config_label)
        except SourceConfig.DoesNotExist:
            _source, _ = Source.objects.get_or_create(
                user_id=user.id,
                defaults={
                    'name': user.username,
                    'long_title': user.username,
                }
            )
            _config, _ = SourceConfig.objects.get_or_create(
                label=_config_label,
                defaults={
                    'source': _source,
                    'transformer_key': transformer_key,
                }
            )
        assert _config.source.user_id == user.id
        assert _config.transformer_key == transformer_key
        return _config


class SourceConfig(models.Model):
    # Previously known as the provider's app_label
    label = models.TextField(unique=True)
    version = models.PositiveIntegerField(default=1)

    source = models.ForeignKey('Source', on_delete=models.CASCADE, related_name='source_configs')
    base_url = models.URLField(null=True)
    transformer_key = models.TextField(null=True)

    disabled = models.BooleanField(default=False)

    objects = SourceConfigManager()

    class JSONAPIMeta(BaseJSONAPIMeta):
        pass

    def natural_key(self):
        return (self.label,)

    def __repr__(self):
        return '<{}({}, {})>'.format(self.__class__.__name__, self.pk, self.label)

    __str__ = __repr__
