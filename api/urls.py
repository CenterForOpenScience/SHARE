from django.conf.urls import url
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import DefaultRouter

from api import views

router = DefaultRouter()

# share routes
router.register(r'v2/extras', views.ExtraDataViewSet, base_name=views.ExtraDataViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/entities', views.EntityViewSet, base_name=views.EntityViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/venues', views.VenueViewSet, base_name=views.VenueViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/organizations', views.OrganizationViewSet, base_name=views.OrganizationViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/publishers', views.PublisherViewSet, base_name=views.PublisherViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/institutions', views.InstitutionViewSet, base_name=views.InstitutionViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/identifiers', views.IdentifierViewSet, base_name=views.IdentifierViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/people', views.PersonViewSet, base_name=views.PersonViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/affiliations', views.AffiliationViewSet, base_name=views.AffiliationViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/contributors', views.ContributorViewSet, base_name=views.ContributorViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/funders', views.FunderViewSet, base_name=views.FunderViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/awards', views.AwardViewSet, base_name=views.AwardViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/tags', views.TagViewSet, base_name=views.TagViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/subjects', views.SubjectViewSet, base_name=views.SubjectViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/links', views.LinkViewSet, base_name=views.LinkViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/creativeworks', views.CreativeWorkViewSet, base_name=views.CreativeWorkViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/preprints', views.PreprintViewSet, base_name=views.PreprintViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/publications', views.PublicationViewSet, base_name=views.PublicationViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/projects', views.ProjectViewSet, base_name=views.ProjectViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/manuscripts', views.ManuscriptViewSet, base_name=views.ManuscriptViewSet.serializer_class.Meta.model._meta.model_name)

# workflow routes
router.register(r'v2/normalizeddata', views.NormalizedDataViewSet, base_name=views.NormalizedDataViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/changesets', views.ChangeSetViewSet, base_name=views.ChangeSetViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/changes', views.ChangeViewSet, base_name=views.ChangeViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/rawdata', views.RawDataViewSet, base_name=views.RawDataViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/users', views.ShareUserViewSet, base_name=views.ShareUserViewSet.serializer_class.Meta.model._meta.model_name)
router.register(r'v2/providers', views.ProviderViewSet, base_name=views.ProviderViewSet.serializer_class.Meta.model._meta.model_name)

urlpatterns = [
    url(r'rss/?', views.CreativeWorksRSS(), name='rss'),
    url(r'atom/?', views.CreativeWorksAtom(), name='atom'),
    url(r'userinfo/?', views.ShareUserView.as_view(), name='userinfo'),
    url(r'search/(?!.*_bulk\/?$)(?P<url_bits>.*)', csrf_exempt(views.ElasticSearchView.as_view()), name='search'),
] + router.urls
