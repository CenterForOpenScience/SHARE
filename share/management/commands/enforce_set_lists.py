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

    def handle(self, *args, **options):
        dry_run = options['dry']
        with self.rollback_unless_commit(options['commit']):
            source_configs = SourceConfig.objects.filter(label__in=options.get('source_configs')).select_related('source')
            for source_config in source_configs:
                self.enforce_blacklist(source_config, dry_run)
                if options['whitelist']:
                    self.enforce_whitelist(source_config, dry_run)

    def enforce_blacklist(self, source_config, dry_run):
        self.stdout.write('\nEnforcing blacklist for {}'.format(source_config.label), style_func=self.style.SUCCESS)

        blacklist = source_config.transformer_kwargs.get('blocked_sets')
        if not blacklist:
            self.stdout.write('{} has no blocked sets, skipping...'.format(source_config.label), style_func=self.style.WARNING)
            return

        bad_through_tags = ThroughTags.objects.filter(
            sources__id=source_config.source.user_id,
            tag__name__in=blacklist
        )

        to_delete = AbstractCreativeWork.objects.filter(
            id__in=bad_through_tags.values_list('creative_work_id'),
            sources__id=source_config.source.user_id,
            is_deleted=False
        ).prefetch_related('sources')

        self.delete_works(to_delete, source_config, dry_run)

    def enforce_whitelist(self, source_config, dry_run):
        self.stdout.write(self.style.SUCCESS('\nEnforcing whitelist for {}'.format(source_config.label)))

        whitelist = source_config.transformer_kwargs.get('approved_sets')
        if not whitelist:
            self.stdout.write('{} has no approved sets, skipping...'.format(source_config.label), style_func=self.style.WARNING)
            return

        good_through_tags = ThroughTags.objects.filter(
            sources__id=source_config.source.user_id,
            tag__name__in=whitelist
        )

        # This will be slooow
        to_delete = AbstractCreativeWork.objects.filter(
            sources__id=source_config.source.user_id,
            is_deleted=False
        ).exclude(
            id__in=good_through_tags.values_list('creative_work_id')
        ).prefetch_related('sources')

        self.delete_works(to_delete, source_config, dry_run)

    def delete_works(self, queryset, source_config, dry_run):
        for work in queryset:
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
