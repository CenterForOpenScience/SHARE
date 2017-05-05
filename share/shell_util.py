from django.contrib.contenttypes.models import ContentType

from share import tasks  # noqa
from share.models import RawDatum
from share.util import IDObfuscator


def get_raws(obj):
    if isinstance(obj, str):
        model, id = IDObfuscator.decode(obj)
    else:
        model = obj._meta.model
        id = obj.id
    return RawDatum.objects.filter(
        normalizeddata__changeset__changes__target_id=id,
        normalizeddata__changeset__changes__target_type=ContentType.objects.get_for_model(model, for_concrete_model=True)
    )


def print_raws(obj):
    for raw in get_raws(obj):
        print(raw.data)
