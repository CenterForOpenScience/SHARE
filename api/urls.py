from django.conf.urls import url
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.routers import DefaultRouter

from api import views

router = DefaultRouter()

# share routes
router.register(r'extras', views.ExtraDataViewSet, base_name=views.ExtraDataViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'entities', views.EntityViewSet, base_name=views.EntityViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'venues', views.VenueViewSet, base_name=views.VenueViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'organizations', views.OrganizationViewSet, base_name=views.OrganizationViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'publishers', views.PublisherViewSet, base_name=views.PublisherViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'institutions', views.InstitutionViewSet, base_name=views.InstitutionViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'identifiers', views.IdentifierViewSet, base_name=views.IdentifierViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'people', views.PersonViewSet, base_name=views.PersonViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'affiliations', views.AffiliationViewSet, base_name=views.AffiliationViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'contributors', views.ContributorViewSet, base_name=views.ContributorViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'funders', views.FunderViewSet, base_name=views.FunderViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'awards', views.AwardViewSet, base_name=views.AwardViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'tags', views.TagViewSet, base_name=views.TagViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'subjects', views.SubjectViewSet, base_name=views.SubjectViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'links', views.LinkViewSet, base_name=views.LinkViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'creativeworks', views.CreativeWorkViewSet, base_name=views.CreativeWorkViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'preprints', views.PreprintViewSet, base_name=views.PreprintViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'publications', views.PublicationViewSet, base_name=views.PublicationViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'projects', views.ProjectViewSet, base_name=views.ProjectViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'manuscripts', views.ManuscriptViewSet, base_name=views.ManuscriptViewSet.serializer_class.Meta.model._meta.model_name)

# registration route
router.register(r'registrations', views.ProviderRegistrationViewSet, base_name=views.ProviderRegistrationViewSet.serializer_class.Meta.model._meta.model_name)

# workflow routes
router.register(r'normalizeddata', views.NormalizedDataViewSet, base_name=views.NormalizedDataViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'changesets', views.ChangeSetViewSet, base_name=views.ChangeSetViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'changes', views.ChangeViewSet, base_name=views.ChangeViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'rawdata', views.RawDataViewSet, base_name=views.RawDataViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'users', views.ShareUserViewSet, base_name=views.ShareUserViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'providers', views.ProviderViewSet, base_name=views.ProviderViewSet.serializer_class.Meta.model._meta.model_name)

urlpatterns = [
    url(r'rss/?', views.CreativeWorksRSS(), name='rss'),
    url(r'atom/?', views.CreativeWorksAtom(), name='atom'),
    url(r'userinfo/?', ensure_csrf_cookie(views.ShareUserView.as_view()), name='userinfo'),
    url(r'search/(?!.*_bulk\/?$)(?P<url_bits>.*)', csrf_exempt(views.ElasticSearchView.as_view()), name='search'),
    url(r'schema/?$', views.SchemaView.as_view(), name='schema'),
    url(r'schema/(?P<model>\w+)', views.ModelSchemaView.as_view(), name='modelschema')
] + router.urls
