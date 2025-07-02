import re


class InvalidID(Exception):
    def __init__(self, value, message='Invalid ID'):
        super().__init__(value, message)
        self.value = value
        self.message = message


class IDObfuscator:
    NUM = 0xDEADBEEF
    MOD = 10000000000
    MOD_INV = 0x17A991C0F
    # Match HHHHH-HHH-HHH Where H is any hexidecimal digit
    ID_RE = re.compile(r'([0-9A-Fa-f]{2,})([0-9A-Fa-f]{3})-([0-9A-Fa-f]{3})-([0-9A-Fa-f]{3})')

    @classmethod
    def encode(cls, instance) -> str:
        return cls.encode_id(instance.id, instance._meta.model)

    @classmethod
    def encode_id(cls, pk, model):
        from django.contrib.contenttypes.models import ContentType

        model_id = ContentType.objects.get_for_model(model).id
        encoded = '{:09X}'.format(pk * cls.NUM % cls.MOD)
        return '{:02X}{}-{}-{}'.format(model_id, encoded[:3], encoded[3:6], encoded[6:])

    @classmethod
    def decode(cls, id):
        from django.contrib.contenttypes.models import ContentType

        match = cls.ID_RE.match(id)
        if not match:
            raise InvalidID(id)
        model_id, *pks = match.groups()

        try:
            model_class = ContentType.objects.get(pk=int(model_id, 16)).model_class()
        except ContentType.DoesNotExist:
            raise InvalidID(id)

        obj_id = int(''.join(pks), 16) * cls.MOD_INV % cls.MOD

        return (model_class, obj_id)

    @classmethod
    def decode_id(cls, id):
        match = cls.ID_RE.match(id)
        if not match:
            raise InvalidID(id)
        model_id, *pks = match.groups()
        return int(''.join(pks), 16) * cls.MOD_INV % cls.MOD

    @classmethod
    def resolve(cls, id):
        model, pk = cls.decode(id)
        return model.objects.get(pk=pk)

    @classmethod
    def resolver(cls, self, args, context, info):
        return cls.resolve(args.get('id', ''))

    @classmethod
    def load(cls, id, *args):
        model, pk = cls.decode(id)
        try:
            return model.objects.get(pk=pk)
        except model.NotFoundError:
            if args:
                return args[0]
            raise


class BaseJSONAPIMeta:
    @classmethod
    def get_id_from_instance(cls, instance):
        return IDObfuscator.encode(instance)

    @classmethod
    def get_instance_from_id(cls, model_class, id):
        try:
            return IDObfuscator.resolve(id)
        except InvalidID:
            return model_class.objects.get(id=id)
