from django.conf.urls import url
from rest_framework.routers import DefaultRouter

from api import views

router = DefaultRouter()

# share routes
router.register(r'extras', views.ExtraDataViewSet, base_name='extradata')
router.register(r'entities', views.EntityViewSet, base_name='entity')
router.register(r'venues', views.VenueViewSet, base_name='venue')
router.register(r'organizations', views.OrganizationViewSet, base_name='organization')
router.register(r'publishers', views.PublisherViewSet, base_name='publisher')
router.register(r'institutions', views.InstitutionViewSet, base_name='institution')
router.register(r'identifiers', views.IdentifierViewSet, base_name='identifier')
router.register(r'people', views.PersonViewSet, base_name='person')
router.register(r'affiliations', views.AffiliationViewSet, base_name='affiliation')
router.register(r'contributors', views.ContributorViewSet, base_name='contributor')
router.register(r'funders', views.FunderViewSet, base_name='funder')
router.register(r'awards', views.AwardViewSet, base_name='award')
router.register(r'tags', views.TagViewSet, base_name='tag')
router.register(r'creative_works', views.CreativeWorkViewSet, base_name='creative_work')
router.register(r'preprints', views.PreprintViewSet, base_name='preprint')
router.register(r'publications', views.PublicationViewSet, base_name='publication')
router.register(r'projects', views.ProjectViewSet, base_name='project')
router.register(r'manuscripts', views.ManuscriptViewSet, base_name='manuscript')

# workflow routes
router.register(r'normalized_data', views.NormalizedDataViewSet, base_name='normalizeddata')
router.register(r'changesets', views.ChangeSetViewSet, base_name='changeset')
router.register(r'changes', views.ChangeViewSet, base_name='change')
router.register(r'raw_data', views.RawDataViewSet, base_name='rawdata')
router.register(r'users', views.ShareUserViewSet, base_name='users')

urlpatterns = [
    url(r'user_info/?', views.ShareUserView.as_view(), name='userinfo'),
    url(r'search/(?P<url_bits>.*)', views.ElasticSearchView.as_view(), name='search'),
] + router.urls
