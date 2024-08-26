from django.core.cache import cache
from django.db import models


class FeatureFlagManager(models.Manager):
    FLAG_CACHE_TIMEOUT_SECONDS = 10

    def flag_is_up(self, flag_name) -> bool:
        '''get whether the named flag is up

        create a FeatureFlag if it doesn't already exist, and cache the result
        '''
        cache_key = self._flag_cache_key(flag_name)
        is_up__cached = cache.get(cache_key)
        if is_up__cached is None:
            (flag, _) = FeatureFlag.objects.get_or_create(name=flag_name)
            cache.set(cache_key, flag.is_up, timeout=self.FLAG_CACHE_TIMEOUT_SECONDS)
            is_up__cached = flag.is_up
        return is_up__cached

    def _flag_cache_key(self, flag_name) -> str:
        return '--'.join((
            self.__class__.__name__,
            flag_name,
        ))


class FeatureFlag(models.Model):
    # flag name constants
    ELASTIC_EIGHT_DEFAULT = 'elastic_eight_default'
    IGNORE_SHAREV2_INGEST = 'ignore_sharev2_ingest'
    SUGGEST_CREATOR_FACET = 'suggest_creator_facet'
    TROVESEARCH_POLYSTRAT = 'trovesearch_polystrat'

    # name _should_ be one of the constants above, but that is not enforced by `choices`
    name = models.TextField(unique=True)
    is_up = models.BooleanField(default=False)

    objects = FeatureFlagManager()

    def __repr__(self):
        return f'{self.__class__.__name__}(name="{self.name}", is_up={self.is_up})'

    __str__ = __repr__

    @property
    def is_defined(self):
        return self.name.lower() == getattr(FeatureFlag, self.name.upper(), None)
