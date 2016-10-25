from graphene.types.scalars import Scalar


# Note should define a couple parse methods but this class is only used for serializing
class JSONField(Scalar):

    @staticmethod
    def serialize(val):
        return val
