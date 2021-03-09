from share.management.commands import BaseShareCommand
from share.models import NormalizedData, RawDatum, ShareUser, SourceUniqueIdentifier
from share.util.graph import MutableGraph
from share.util.osf import osf_sources, guess_osf_guid


CHUNK_SIZE = 2000


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

    print(f'normd {normalized_datum.id}: updating suid from {existing_suid.id} to {new_suid.id}...')
    update_old_suid_raws(normalized_datum, existing_suid, new_suid)
    existing_suid.delete()


def update_old_suid_raws(old_suid, new_suid):
    for raw_datum in list(RawDatum.objects.defer('datum').filter(suid=old_suid)):
        # RawDatum is unique on (suid, sha256), so there will be 0 or 1 duplicates
        duplicate_raw = RawDatum.objects.filter(suid=new_suid, sha256=raw_datum.sha256).first()

        if duplicate_raw:
            if duplicate_raw == raw_datum:
                raise Exception(f'wtf the duplicate is the same one (rawd:{raw_datum}, old_suid:{old_suid}, new_suid:{new_suid})')
            print(f'> rawd {raw_datum.id}: deleting in favor of dupe => {duplicate_raw.id}')
            NormalizedData.objects.filter(raw=raw_datum).update(raw=duplicate_raw)
            raw_datum.delete()
        else:
            print(f'> rawd {raw_datum.id}: update suid ({old_suid.id} => {new_suid.id})')
            raw_datum.suid = new_suid
            raw_datum.save(update_fields=['suid'])


def get_normd_ids(start_id):
    normd_id_qs = NormalizedData.objects.filter(
        id__gte=start_id,
        raw__isnull=False,
        source__in=ShareUser.objects.filter(source__in=osf_sources())
    ).order_by('id').values_list('id', flat=True)
    return list(normd_id_qs[:CHUNK_SIZE])


class Command(BaseShareCommand):
    def add_arguments(self, parser):
        parser.add_argument('--commit', action='store_true', help='Should the script actually commit?')
        parser.add_argument('--start-id', type=int, default=0, help='NormalizedData id to begin at')

    def handle(self, *args, **options):
        commit = options.get('commit')
        start_id = options['start_id']

        normd_ids = get_normd_ids(start_id)
        while normd_ids:
            for normd_id in normd_ids:
                normd = NormalizedData.objects.get(id=normd_id)
                mgraph = MutableGraph.from_jsonld(normd.data)
                guid = guess_osf_guid(mgraph)
                if guid:
                    with self.rollback_unless_commit(commit=commit):
                        update_suid(normd, guid)
            next_start_id = int(normd_ids[-1]) + 1
            print(f'-- next normd chunk starting with {next_start_id} --')
            normd_ids = get_normd_ids(next_start_id)
