from rest_framework import viewsets, permissions
from share import serializers


class VenueViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, ]  # TokenHasScope]
    serializer_class = serializers.VenueSerializer
    # TODO: Add in scopes once we figure out who, why, and how.
    # required_scopes = ['', ]
    queryset = serializer_class.Meta.model.objects.all()


class InstitutionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, ]  # TokenHasScope]
    serializer_class = serializers.InstitutionSerializer
    # TODO: Add in scopes once we figure out who, why, and how.
    # required_scopes = ['', ]
    queryset = serializer_class.Meta.model.objects.all()


class FunderViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, ]  # TokenHasScope]
    serializer_class = serializers.FunderSerializer
    # TODO: Add in scopes once we figure out who, why, and how.
    # required_scopes = ['', ]
    queryset = serializer_class.Meta.model.objects.all()


class AwardViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, ]  # TokenHasScope]
    serializer_class = serializers.AwardSerializer
    # TODO: Add in scopes once we figure out who, why, and how.
    # required_scopes = ['', ]
    queryset = serializer_class.Meta.model.objects.all()


class DataProviderViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, ]  # TokenHasScope]
    serializer_class = serializers.DataProviderSerializer
    # TODO: Add in scopes once we figure out who, why, and how.
    # required_scopes = ['', ]
    queryset = serializer_class.Meta.model.objects.all()


class TaxonomyViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, ]  # TokenHasScope]
    serializer_class = serializers.TaxonomySerializer
    # TODO: Add in scopes once we figure out who, why, and how.
    # required_scopes = ['', ]
    queryset = serializer_class.Meta.model.objects.all()


class TagViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, ]  # TokenHasScope]
    serializer_class = serializers.TagSerializer
    # TODO: Add in scopes once we figure out who, why, and how.
    # required_scopes = ['', ]
    queryset = serializer_class.Meta.model.objects.all()


class CreativeWorkViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, ]  # TokenHasScope]
    serializer_class = serializers.CreativeWorkSerializer
    # TODO: Add in scopes once we figure out who, why, and how.
    # required_scopes = ['', ]
    queryset = serializer_class.Meta.model.objects.all()


class PreprintViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, ]  # TokenHasScope]
    serializer_class = serializers.PreprintSerializer
    # TODO: Add in scopes once we figure out who, why, and how.
    # required_scopes = ['', ]
    queryset = serializer_class.Meta.model.objects.all()


class ManuscriptViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, ]  # TokenHasScope]
    serializer_class = serializers.ManuscriptSerializer
    # TODO: Add in scopes once we figure out who, why, and how.
    # required_scopes = ['', ]
    queryset = serializer_class.Meta.model.objects.all()
