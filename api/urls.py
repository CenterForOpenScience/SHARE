from django.conf.urls import url
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import ensure_csrf_cookie

from rest_framework.routers import DefaultRouter

from graphene_django.views import GraphQLView

from share import models

from api import views
from api.serializers import BaseShareSerializer
from api.views.share import ShareObjectViewSet

router = DefaultRouter()


def register_route(prefix, viewset):
    router.register(prefix, viewset, base_name=viewset.serializer_class.Meta.model._meta.model_name)


class EndpointGenerator:

    def __init__(self):
        subclasses = models.ShareObject.__subclasses__()

        generated_endpoints = []
        for subclass in subclasses:
            if not (subclass._meta.proxied_children and subclass is subclass._meta.concrete_model):
                generated_endpoints.append(subclass)
            elif (subclass._meta.proxied_children and subclass is subclass._meta.concrete_model):
                generated_endpoints.extend(subclass.get_type_classes())

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
        register_route(route_name, viewset)

# generated model routes
EndpointGenerator()

# registration route
register_route(r'sourceregistrations', views.ProviderRegistrationViewSet)

# site banners route
register_route(r'site_banners', views.SiteBannerViewSet)

# workflow routes
register_route(r'rawdata', views.RawDatumViewSet)
register_route(r'user', views.ShareUserViewSet)
register_route(r'sources', views.SourceViewSet)

router.register(r'normalizeddata', views.NormalizedDataViewSet, base_name='normalizeddata')

model_schema_patterns = [
    url(r'schema/{}/?'.format(v.MODEL.__name__), v.as_view())
    for v in views.ModelSchemaView.model_views
]

urlpatterns = [
    url(r'status/?', views.ServerStatusView.as_view(), name='status'),
    url(r'rss/?', views.CreativeWorksRSS(), name='rss'),
    url(r'atom/?', views.CreativeWorksAtom(), name='atom'),
    url(r'graph/?', GraphQLView.as_view(graphiql=True)),
    url(r'userinfo/?', ensure_csrf_cookie(views.ShareUserView.as_view()), name='userinfo'),

    # only match _count and _search requests
    url(
        r'search/(?P<url_bits>(?:\w+/)?_(?:search|count)/?)$',
        csrf_exempt(views.ElasticSearchView.as_view()),
        name='search'
    ),
    # match _suggest requests
    url(
        r'search/(?P<url_bits>(?:\w+/)?_(?:suggest)/?)$',
        csrf_exempt(views.ElasticSearchPostOnlyView.as_view()),
        name='search_post'
    ),
    # match _mappings requests
    url(
        r'search/(?P<url_bits>_mappings(/.+|$|/))',
        csrf_exempt(views.ElasticSearchGetOnlyView.as_view()),
        name='search_get'
    ),
    url(
        r'search/(?P<url_bits>.*)',
        csrf_exempt(views.ElasticSearch403View.as_view()),
        name='search_403'
    ),

    url(r'schema/?$', views.SchemaView.as_view(), name='schema'),
    url(r'schema/creativework/hierarchy/?$', views.ModelTypesView.as_view(), name='modeltypes'),
    *model_schema_patterns
] + router.urls
