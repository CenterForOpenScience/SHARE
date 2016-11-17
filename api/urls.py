from django.conf.urls import url
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import ensure_csrf_cookie

from rest_framework.routers import DefaultRouter

from graphene_django.views import GraphQLView

from share import models
from share.serializers import BaseShareSerializer

from api import views
from api.views.share import ShareObjectViewSet

router = DefaultRouter()


def register_route(prefix, viewset):
    router.register(prefix, viewset, base_name=viewset.serializer_class.Meta.model._meta.model_name)


class EndpointGenerator:

    def __init__(self):
        subclasses = models.ShareObject.__subclasses__()

        generated_endpoints = []
        for subclass in subclasses:
            if not (subclass._meta.proxied_children and subclass == subclass._meta.concrete_model):
                generated_endpoints += [subclass]
            elif (subclass._meta.proxied_children and subclass == subclass._meta.concrete_model):
                generated_endpoints += subclass.get_type_classes()

        self.generate_endpoints(generated_endpoints)

    def generate_endpoints(self, subclasses):
        for subclass in subclasses:
            self.generate_serializer(subclass)

    def generate_serializer(self, subclass):
        class_name = subclass.__name__ + 'Serializer'
        meta_class = type('Meta', (BaseShareSerializer.Meta,), {'model': subclass})
        generated_serializer = type(class_name, (BaseShareSerializer,), {
            'Meta': meta_class
        })
        globals().update({class_name: generated_serializer})
        self.generate_viewset(subclass, generated_serializer)

    def generate_viewset(self, subclass, serializer):
        class_name = subclass.__name__ + 'ViewSet'
        generated_viewset = type(class_name, (ShareObjectViewSet,), {
            'serializer_class': serializer,
            'queryset': serializer.Meta.model.objects.all().select_related('extra')

        })
        globals().update({class_name: generated_viewset})
        self.register_url(subclass, generated_viewset)

    def register_url(self, subclass, viewset):
        route_name = subclass.__name__.lower()
        register_route(route_name, viewset)

# generated model routes
EndpointGenerator()

# registration route
register_route(r'registrations', views.ProviderRegistrationViewSet)

# workflow routes
register_route(r'changeset', views.ChangeSetViewSet)
register_route(r'change', views.ChangeViewSet)
register_route(r'rawdata', views.RawDataViewSet)
register_route(r'user', views.ShareUserViewSet)
register_route(r'sources', views.ProviderViewSet)

router.register(r'normalizeddata', views.NormalizedDataViewSet, base_name='normalizeddata')

urlpatterns = [
    url(r'rss/?', views.CreativeWorksRSS(), name='rss'),
    url(r'atom/?', views.CreativeWorksAtom(), name='atom'),
    url(r'graph/?', GraphQLView.as_view(graphiql=True)),
    url(r'userinfo/?', ensure_csrf_cookie(views.ShareUserView.as_view()), name='userinfo'),
    url(r'search/(?!.*_bulk\/?$)(?P<url_bits>.*)', csrf_exempt(views.ElasticSearchView.as_view()), name='search'),
    url(r'schema/?$', views.SchemaView.as_view(), name='schema'),
    url(r'schema/(?P<model>\w+)', views.ModelSchemaView.as_view(), name='modelschema'),
] + router.urls
