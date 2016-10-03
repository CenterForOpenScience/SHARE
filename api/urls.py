from django.conf.urls import url
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import DefaultRouter

from api import views

router = DefaultRouter()


def register_route(prefix, viewset):
    router.register(prefix, viewset, base_name=viewset.serializer_class.Meta.model._meta.model_name)


def register_creative_work_route(prefix, model):
    register_route(prefix, views.make_creative_work_view_set_class(model))


# share routes
register_route(r'extras', views.ExtraDataViewSet)
register_route(r'entities', views.EntityViewSet)
register_route(r'venues', views.VenueViewSet)
register_route(r'organizations', views.OrganizationViewSet)
register_route(r'publishers', views.PublisherViewSet)
register_route(r'institutions', views.InstitutionViewSet)
#register_route(r'identifiers', views.IdentifierViewSet)
register_route(r'people', views.PersonViewSet)
register_route(r'affiliations', views.AffiliationViewSet)
register_route(r'contributors', views.ContributorViewSet)
register_route(r'funders', views.FunderViewSet)
register_route(r'awards', views.AwardViewSet)
register_route(r'tags', views.TagViewSet)
register_route(r'subjects', views.SubjectViewSet)
register_creative_work_route(r'creativeworks', 'creativework')
register_creative_work_route(r'articles', 'article')
register_creative_work_route(r'books', 'book')
register_creative_work_route(r'conferencepapers', 'conferencepaper')
register_creative_work_route(r'datasets', 'dataset')
register_creative_work_route(r'dissertations', 'dissertation')
register_creative_work_route(r'lessons', 'lesson')
register_creative_work_route(r'posters', 'poster')
register_creative_work_route(r'preprints', 'preprint')
register_creative_work_route(r'presentations', 'presentation')
register_creative_work_route(r'projects', 'project')
register_creative_work_route(r'projectregistrations', 'projectregistration')
register_creative_work_route(r'reports', 'report')
register_creative_work_route(r'sections', 'section')
register_creative_work_route(r'software', 'software')
register_creative_work_route(r'theses', 'thesis')
register_creative_work_route(r'workingpapers', 'workingpaper')

# registration route
register_route(r'registrations', views.ProviderRegistrationViewSet)

# workflow routes
register_route(r'normalizeddata', views.NormalizedDataViewSet)
register_route(r'changesets', views.ChangeSetViewSet)
register_route(r'changes', views.ChangeViewSet)
register_route(r'rawdata', views.RawDataViewSet)
register_route(r'users', views.ShareUserViewSet)
register_route(r'providers', views.ProviderViewSet)

urlpatterns = [
    url(r'rss/?', views.CreativeWorksRSS(), name='rss'),
    url(r'atom/?', views.CreativeWorksAtom(), name='atom'),
    url(r'userinfo/?', views.ShareUserView.as_view(), name='userinfo'),
    url(r'search/(?!.*_bulk\/?$)(?P<url_bits>.*)', csrf_exempt(views.ElasticSearchView.as_view()), name='search'),
    url(r'schema/?$', views.SchemaView.as_view(), name='schema'),
    url(r'schema/(?P<model>\w+)', views.ModelSchemaView.as_view(), name='modelschema'),
    url(r'relationtypes/?', views.RelationTypesView.as_view(), name='relationtypes')
] + router.urls
