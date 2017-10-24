from typedmodels.models import TypedModel

from rest_framework.utils.field_mapping import get_detail_view_name

from share import models

from api import fields
from api.shareobjects.serializers import ShareObjectSerializer
from api.shareobjects.views import ShareObjectViewSet


class EndpointGenerator:

    def __init__(self, router):
        self._router = router
        subclasses = models.ShareObject.__subclasses__()

        generated_endpoints = []
        for subclass in subclasses:
            if issubclass(subclass, TypedModel) and subclass._meta.concrete_model is subclass:
                generated_endpoints.extend(subclass.get_type_classes())
            else:
                generated_endpoints.append(subclass)
        self.generate_endpoints(generated_endpoints)

    def generate_endpoints(self, subclasses):
        for subclass in subclasses:
            self.generate_serializer(subclass)

    def generate_serializer(self, subclass):
        class_name = subclass.__name__ + 'Serializer'
        meta_class = type('Meta', tuple(), {'model': subclass, 'fields': '__all__'})
        generated_serializer = type(class_name, (ShareObjectSerializer,), {
            'Meta': meta_class,
            'type': fields.TypeField(),
            'url': fields.ShareIdentityField(view_name='api:{}'.format(get_detail_view_name(subclass)))
        })
        globals().update({class_name: generated_serializer})
        self.generate_viewset(subclass, generated_serializer)

    def generate_viewset(self, subclass, serializer):
        class_name = subclass.__name__ + 'ViewSet'
        # Pre-join all fields foreign keys
        # Note: we can probably avoid this all together if we fix DRF
        # We don't need to load the entire objects, just the PKs
        queryset = serializer.Meta.model.objects.all().select_related(*(
            field.name for field in serializer.Meta.model._meta.get_fields()
            if field.is_relation and field.editable and not field.many_to_many
        ))
        if subclass.__name__ == 'AgentIdentifier':
            queryset = queryset.exclude(scheme='mailto')

        generated_viewset = type(class_name, (ShareObjectViewSet,), {
            'queryset': queryset,
            'serializer_class': serializer,
        })
        globals().update({class_name: generated_viewset})
        self.register_url(subclass, generated_viewset)

    def register_url(self, subclass, viewset):
        route_name = subclass._meta.verbose_name_plural.replace(' ', '')
        self._router.register(route_name, viewset, base_name=viewset.serializer_class.Meta.model._meta.model_name)
