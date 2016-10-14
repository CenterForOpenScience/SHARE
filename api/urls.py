from django.conf.urls import url
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import DefaultRouter

from api import views

router = DefaultRouter()


def register_route(prefix, viewset):
    router.register(prefix, viewset, base_name=viewset.serializer_class.Meta.model._meta.model_name)


def register_creative_work_route(model_name):
    register_route(model_name, views.make_creative_work_view_set_class(model_name))


# creative work routes
register_creative_work_route(r'creativework')
register_creative_work_route(r'article')
register_creative_work_route(r'book')
register_creative_work_route(r'conferencepaper')
register_creative_work_route(r'dataset')
register_creative_work_route(r'dissertation')
register_creative_work_route(r'lesson')
register_creative_work_route(r'poster')
register_creative_work_route(r'preprint')
register_creative_work_route(r'presentation')
register_creative_work_route(r'project')
register_creative_work_route(r'projectregistration')
register_creative_work_route(r'report')
register_creative_work_route(r'section')
register_creative_work_route(r'software')
register_creative_work_route(r'thesis')
register_creative_work_route(r'workingpaper')

# creative work attributes
register_route(r'tag', views.TagViewSet)
register_route(r'subject', views.SubjectViewSet)
register_route(r'venue', views.VenueViewSet)
register_route(r'extra', views.ExtraDataViewSet)

# entity routes
register_route(r'person', views.PersonViewSet)
register_route(r'organization', views.OrganizationViewSet)
register_route(r'institution', views.InstitutionViewSet)

# identifier routes
register_route(r'entityidentifier', views.EntityIdentifierViewSet)
register_route(r'workidentifier', views.WorkIdentifierViewSet)

# relation routes
register_route(r'entityrelation', views.EntityRelationViewSet)
register_route(r'workrelation', views.WorkRelationViewSet)
register_route(r'contribution', views.ContributionViewSet)
register_route(r'award', views.AwardViewSet)

# registration route
register_route(r'registrations', views.ProviderRegistrationViewSet)

# workflow routes
register_route(r'normalizeddata', views.NormalizedDataViewSet)
register_route(r'changeset', views.ChangeSetViewSet)
register_route(r'change', views.ChangeViewSet)
register_route(r'rawdata', views.RawDataViewSet)
register_route(r'user', views.ShareUserViewSet)
register_route(r'provider', views.ProviderViewSet)

urlpatterns = [
    url(r'rss/?', views.CreativeWorksRSS(), name='rss'),
    url(r'atom/?', views.CreativeWorksAtom(), name='atom'),
    url(r'userinfo/?', views.ShareUserView.as_view(), name='userinfo'),
    url(r'search/(?!.*_bulk\/?$)(?P<url_bits>.*)', csrf_exempt(views.ElasticSearchView.as_view()), name='search'),
    url(r'schema/?$', views.SchemaView.as_view(), name='schema'),
    url(r'schema/(?P<model>\w+)', views.ModelSchemaView.as_view(), name='modelschema'),
] + router.urls
