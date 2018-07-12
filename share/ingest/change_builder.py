import logging
import pendulum
import datetime

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from share.disambiguation import GraphDisambiguator
from share.models import Change, ChangeSet
from share.util import IDObfuscator


logger = logging.getLogger(__name__)


class ChangeBuilder:

    @classmethod
    def build_change_set(cls, graph, normalized_datum, instance_map=None, disambiguate=False):
        assert not (instance_map and disambiguate), 'Either provide instance_map or disambiguate=True, not both'

        user = normalized_datum.source  # "source" here is a ShareUser
        source = user.source

        if disambiguate:
            instance_map = GraphDisambiguator(source).find_instances(graph)
        elif instance_map is None:
            instance_map = {}

        differs = [cls(n, source, instance_map) for n in graph.topologically_sorted()]

        if all(d.diff is None for d in differs):
            logger.debug('No changes detected in {!r}, skipping.'.format(graph))
            return None

        change_set = ChangeSet(normalized_data_id=normalized_datum.id)
        change_set.save()

        Change.objects.bulk_create(
            filter(None, [
                d.build_change(change_set, save=False)
                for d in differs
            ])
        )

        return change_set

    def __init__(self, node, source=None, instance_map=None):
        self.node = node
        self.source = source
        self.instance_map = instance_map or {}

        self.instance = self._get_instance(node)
        self.diff = self.get_diff() if not self.should_skip() else None

    def build_change(self, change_set, save=True):
        if self.diff is None:
            logger.debug('No changes detected in {!r}, skipping.'.format(self.node))
            return None

        model = self.node.model

        attrs = {
            'node_id': self.node.id,
            'change': self.diff,
            'change_set': change_set,
            'model_type': ContentType.objects.get_for_model(model, for_concrete_model=False),
            'target_type': ContentType.objects.get_for_model(model, for_concrete_model=True),
            'target_version_type': ContentType.objects.get_for_model(model.VersionModel, for_concrete_model=True),
        }

        if not self.instance:
            attrs['type'] = Change.TYPE.create
        else:
            attrs['type'] = Change.TYPE.update
            attrs['target_id'] = self.instance.pk
            attrs['target_version_id'] = self.instance.version_id

        change = Change(**attrs)

        if save:
            change.save()

        return change

    def should_skip(self):
        if not hasattr(self.node.model, 'VersionModel'):
            # Non-ShareObjects (e.g. SubjectTaxonomy) cannot be changed.
            # Shouldn't reach this point...
            logger.warn('Change node {!r} targets immutable model {}, skipping.'.format(self.node, self.node.model))
            return True

        if self.instance:
            if (self.node.type == 'subject'
                    and self.instance.central_synonym is None
                    and (not self.source or self.source.user.username != settings.APPLICATION_USERNAME)):
                return True

        return False

    def get_diff(self):
        attrs = self.node.attrs()
        relations = self.node.relations(in_edges=False)

        new_extra = attrs.pop('extra', None)
        if new_extra and self.source and self.source.user:
            # Only save "extra" data that has a namespace
            extra_namespace = self.source.user.username

            old_extra = getattr(self.instance, 'extra', None)
            if old_extra:
                old_extra = old_extra.data.get(extra_namespace, {})

                # NOTE extra changes are only diffed at the top level
                extra_diff = {
                    k: v
                    for k, v in new_extra.items()
                    if k not in old_extra or old_extra[k] != v
                }
                if extra_diff:
                    attrs['extra'] = extra_diff
            else:
                attrs['extra'] = new_extra

        if self.instance is None:
            return self._diff_for_create(attrs, relations)
        return self._diff_for_update(attrs, relations)

    def _diff_for_create(self, attrs, relations):
        return {
            **attrs,
            **self._relations_to_jsonld(relations),
        }

    def _diff_for_update(self, attrs, relations):
        assert self.instance, 'Do not call _diff_for_update without self.instance set'
        attrs_diff, relations_diff = {}, {}

        ignore_attrs = self._get_ignore_attrs(attrs)

        new_model = self.node.model
        old_model = type(self.instance)
        if '@type' not in ignore_attrs and old_model is not new_model:
            if (
                    len(new_model.__mro__) >= len(old_model.__mro__)

                    # Special case to allow creators to be downgraded to contributors
                    # This allows OSF users to mark project contributors as bibiliographic or non-bibiliographic
                    # and have that be reflected in SHARE
                    or issubclass(new_model, apps.get_model('share', 'contributor'))
            ):
                attrs_diff['@type'] = new_model._meta.label_lower

        for k, v in attrs.items():
            if k in ignore_attrs:
                logger.debug('Ignoring potentially conflicting change to "%s"', k)
                continue
            old_value = getattr(self.instance, k)
            if isinstance(old_value, datetime.datetime):
                v = pendulum.parse(v)
            if v != old_value:
                attrs_diff[k] = v.isoformat() if isinstance(v, datetime.datetime) else v

        # TODO Add relationships in for non-subjects. Somehow got omitted first time around
        if new_model is apps.get_model('share', 'subject'):
            for k, v in relations.items():
                old_value = getattr(self.instance, k)
                if old_value != self._get_instance(v):
                    relations_diff[k] = v

        diff = {
            **attrs_diff,
            **self._relations_to_jsonld(relations_diff),
        }
        # If there's nothing to update, return None instead of an empty diff
        if not diff:
            new_source = (
                self.source
                and hasattr(self.instance, 'sources')
                and not self.instance.sources.filter(source=self.source).exists()
            )
            if not new_source:
                return None
        return diff

    def _get_instance(self, node):
        return self.instance_map.get(node) or self.instance_map.get(node.id)

    def _relations_to_jsonld(self, relations):
        def refs(n):
            if isinstance(n, list):
                return [refs(node) for node in n]
            instance = self._get_instance(n)
            return {
                '@id': IDObfuscator.encode(instance) if instance else n.id,
                '@type': n.type,
            }
        return {
            k: refs(v)
            for k, v in relations.items()
        }

    def _get_ignore_attrs(self, attrs):
        ignore_attrs = set()

        if not issubclass(self.node.model, apps.get_model('share', 'creativework')):
            # Only work records get special treatment at the moment
            return ignore_attrs

        # Hacky fix for SHARE-604
        # If the given date_updated is older than the current one, don't accept any changes that would overwrite newer changes
        if 'date_updated' in attrs and self.instance.date_updated:
            date_updated = pendulum.parse(attrs['date_updated'])
            if date_updated < self.instance.date_updated:
                logger.warning('%s appears to be from the past, change date_updated (%s) is older than the current (%s). Ignoring conflicting changes.', self.node, attrs['date_updated'], self.instance.date_updated)
                # Just in case
                ignore_attrs.update(self.instance.change.change.keys())

                # Go back until we find a change that is older than us
                for version in self.instance.versions.select_related('change').iterator():
                    if not version.date_updated or date_updated > version.date_updated:
                        break
                    ignore_attrs.update(version.change.change.keys())

        # If we get changes from a source that hasn't been marked as canonical
        # don't allow attributes set by canonical sources to be changed.
        # Stops aggregators from overwriting the most correct information
        # IE CrossRef sometimes turns preprints into articles/publications
        # TODO Write a test case for subjects
        if self.source and not self.source.canonical and hasattr(self.instance, 'sources'):
            # Only fetch 15. If there are more than 15, it's probably a bug. Even if it is not, the past 15 changes should be enough...
            prev_changes = list(
                self.instance.changes.filter(
                    change_set__normalized_data__source__source__canonical=True
                ).values_list(
                    'change',
                    flat=True
                )[:15]
            )
            canonical_keys = set(key for change in prev_changes for key in change.keys())
            if prev_changes and set(attrs.keys()) & canonical_keys:
                canonical_sources = list(
                    self.instance.sources.filter(
                        source__canonical=True
                    ).values_list('username', flat=True)
                )
                logger.warning('Recieved changes from a non-canonical source %s that conflict with one of %s. Ignoring conflicting changes', self.source, canonical_sources)
                ignore_attrs.update(canonical_keys)

                # Appears that type doesn't get added to changes or at least the first change
                # Safe to assume the type was set by the canonical source
                ignore_attrs.add('@type')

        return ignore_attrs
