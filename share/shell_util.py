from django.contrib.contenttypes.models import ContentType
from share.models import RawData
from share.util import IDObfuscator


def print_raws(object):
    if isinstance(object, str):
        model, id = IDObfuscator.decode(object)
    else:
        model = object._meta.model
        id = object.id
    raws = RawData.objects.filter(
        normalizeddata__changeset__changes__target_id=id,
        normalizeddata__changeset__changes__target_type=ContentType.objects.get_for_model(model, for_concrete_model=True)
    )
    for raw in raws:
        print(raw.data)
