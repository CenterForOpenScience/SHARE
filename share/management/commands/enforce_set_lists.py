from django.db.models import Q
from share.management.commands import BaseShareCommand
from share.models import SourceConfig, AbstractCreativeWork, ThroughTags
from share.util import IDObfuscator


class Command(BaseShareCommand):
    """Enforce set whitelist and blacklist for the given source config(s)

    Look at each source config's `transformer_kwargs` for `approved_sets` and `blocked_sets`.
    Find and delete works in the database from that source that would not have been allowed,
    according to those lists. If the work was ingested from multiple sources, remove the given
    source from it instead of deleting.

    By default enforce blacklists only, because enforcing whitelists is slooow.
    Pass --whitelist to enforce whitelists too.
    """

    def add_arguments(self, parser):
        parser.add_argument('source_configs', nargs='+', type=str, help='Labels of the source configs to enforce')
        parser.add_argument('--dry', action='store_true', help='Print changes that would be made, but make no changes')
        parser.add_argument('--commit', action='store_true', help='If omitted, roll back the transaction after making changes')
        parser.add_argument('--whitelist', action='store_true', help='Enforce whitelist too -- will be slow')
        parser.add_argument('--delete-related', action='store_true', help='When deleting a work, also delete related works')
        parser.add_argument('--superfluous', action='store_true', help='Reprocess already deleted works')

    def handle(self, *args, **options):
        source_configs = options['source_configs']
        dry_run = options['dry']
        commit = options['commit']
        delete_related = options['delete_related']
        superfluous = options['superfluous']

        with self.rollback_unless_commit(commit):
            source_configs = SourceConfig.objects.filter(label__in=source_configs).select_related('source')
            for source_config in source_configs:
                self.stdout.write('\nEnforcing blacklist for {}'.format(source_config.label), style_func=self.style.SUCCESS)
                to_delete = self.enforce_blacklist_qs(source_config)
                if to_delete is not None:
                    self.delete_works(to_delete, source_config, dry_run, superfluous, delete_related)

                if options['whitelist']:
                    self.stdout.write('\nEnforcing whitelist for {}'.format(source_config.label), style_func=self.style.SUCCESS)
                    to_delete = self.enforce_whitelist_qs(source_config)
                    if to_delete is not None:
                        self.delete_works(to_delete, source_config, dry_run, superfluous, delete_related)

    def enforce_blacklist_qs(self, source_config):
        blacklist = source_config.transformer_kwargs.get('blocked_sets') if source_config.transformer_kwargs else None
        if not blacklist:
            self.stdout.write('{} has no blocked sets, skipping...'.format(source_config.label), style_func=self.style.WARNING)
            return

        bad_through_tags = ThroughTags.objects.filter(
            sources__id=source_config.source.user_id,
            tag__name__in=blacklist
        )

        return AbstractCreativeWork.objects.filter(
            id__in=bad_through_tags.values_list('creative_work_id'),
            sources__id=source_config.source.user_id,
        )

    def enforce_whitelist_qs(self, source_config):
        whitelist = source_config.transformer_kwargs.get('approved_sets') if source_config.transformer_kwargs else None
        if not whitelist:
            self.stdout.write('{} has no approved sets, skipping...'.format(source_config.label), style_func=self.style.WARNING)
            return

        good_through_tags = ThroughTags.objects.filter(
            sources__id=source_config.source.user_id,
            tag__name__in=whitelist
        )

        # This will be slooow
        return AbstractCreativeWork.objects.filter(
            sources__id=source_config.source.user_id,
        ).exclude(
            id__in=good_through_tags.values_list('creative_work_id')
        )

    def delete_works(self, works_qs, source_config, dry_run, superfluous, delete_related):
        works_deleted = []

        if not superfluous:
            works_qs = works_qs.filter(is_deleted=False)
        for work in works_qs.prefetch_related('sources'):
            works_deleted.append(work.id)
            # If we've heard about the work from another source, just remove this source from it instead of deleting
            if len(work.sources.all()) > 1:
                self.stdout.write('{}: {}'.format(
                    self.style.WARNING('Removing {} from {}'.format(source_config.source.name, IDObfuscator.encode(work))),
                    work.title
                ))
                if not dry_run:
                    work.sources.remove(source_config.source.user)
                    # poke it to reindex
                    work.administrative_change(allow_empty=True)
            else:
                self.stdout.write('{}: {}'.format(
                    self.style.NOTICE('Deleting work {}'.format(IDObfuscator.encode(work))),
                    work.title
                ))
                if not dry_run:
                    work.administrative_change(is_deleted=True)
        self.stdout.write('\nProcessed {} works!'.format(len(works_deleted)), style_func=self.style.SUCCESS)
        if not delete_related:
            return

        self.stdout.write('\nNow deleting related works...\n')

        related_works = AbstractCreativeWork.objects.filter(
            Q(incoming_creative_work_relations__subject_id__in=works_deleted) | Q(outgoing_creative_work_relations__related_id__in=works_deleted),
            is_deleted=False,
            sources__id=source_config.source.user_id
        ).prefetch_related('sources')

        # Traverse related works only one level deep, please
        self.delete_works(related_works, source_config, dry_run, superfluous, False)
