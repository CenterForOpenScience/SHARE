from share.management.commands import BaseShareCommand
from share.models import NormalizedData, RawDatum, ShareUser, SourceUniqueIdentifier
from share.util.graph import MutableGraph
from share.util.osf import osf_sources, guess_osf_guid


def update_suid(normalized_datum, new_suid_identifier):
    raw_datum = normalized_datum.raw
    if not raw_datum:
        print(f'normd {normalized_datum.id}: skip, no raw')
        return

    existing_suid = raw_datum.suid
    new_suid, created = SourceUniqueIdentifier.objects.get_or_create(
        identifier=new_suid_identifier,
        source_config_id=existing_suid.source_config_id,
    )

    if new_suid == existing_suid:
        print(f'normd {normalized_datum.id}: skip, already has correct suid {existing_suid.id}')
        return

    # RawDatum is unique on (suid, sha256), so there will be 0 or 1 duplicates
    duplicate_raw = RawDatum.objects.filter(suid=new_suid, sha256=raw_datum.sha256).first()

    if duplicate_raw:
        if duplicate_raw == raw_datum:
            raise Exception(f'wtf the duplicate is the same one ({raw_datum}, {duplicate_raw})')
        print(f'normd {normalized_datum.id}: handle dupe raw ({raw_datum.id} => {duplicate_raw.id})')
        normalized_datum.raw = duplicate_raw
        normalized_datum.save()
        raw_datum.delete()
    else:
        print(f'normd {normalized_datum.id}: update suid ({existing_suid.id} => {new_suid.id})')
        raw_datum.suid = new_suid
        raw_datum.save()
    existing_suid.delete()


class Command(BaseShareCommand):
    def add_arguments(self, parser):
        parser.add_argument('--commit', action='store_true', help='Should the script actually commit?')
        parser.add_argument('--start-id', type=int, default=0, help='NormalizedData id to begin at')
        parser.add_argument('--max-datums', type=int, help='NormalizedData id to begin at')

    def handle(self, *args, **options):
        commit = options.get('commit')
        max_datums = options.get('max_datums', None)
        start_id = options['start_id']

        nd_qs = NormalizedData.objects.filter(
            id__gte=start_id,
            source__in=ShareUser.objects.filter(source__in=osf_sources())
        ).select_related(
            'source',
            'raw',
            'raw__suid',
        ).order_by('id')

        if max_datums:
            nd_qs = nd_qs[:max_datums]

        nd_iterator = nd_qs.iterator()

        for nd in nd_iterator:
            mgraph = MutableGraph.from_jsonld(nd.data)
            guid = guess_osf_guid(mgraph)
            if guid:
                with self.rollback_unless_commit(commit=commit):
                    update_suid(nd, guid)
