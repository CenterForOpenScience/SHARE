from rest_framework.routers import DefaultRouter

from api import views

router = DefaultRouter()

# share routes
router.register(r'extra', views.ExtraDataViewSet, base_name='extradata')
router.register(r'entity', views.EntityViewSet, base_name='entity')
router.register(r'venue', views.VenueViewSet, base_name='venue')
router.register(r'organization', views.OrganizationViewSet, base_name='organization')
router.register(r'publisher', views.PublisherViewSet, base_name='publisher')
router.register(r'institution', views.InstitutionViewSet, base_name='institution')
router.register(r'identifier', views.IdentifierViewSet, base_name='identifier')
router.register(r'person', views.PersonViewSet, base_name='person')
router.register(r'affiliation', views.AffiliationViewSet, base_name='affiliation')
router.register(r'contributor', views.ContributorViewSet, base_name='contributor')
router.register(r'funder', views.FunderViewSet, base_name='funder')
router.register(r'award', views.AwardViewSet, base_name='award')
router.register(r'tag', views.TagViewSet, base_name='tag')
router.register(r'creative_work', views.CreativeWorkViewSet, base_name='creative_work')
router.register(r'preprint', views.PreprintViewSet, base_name='preprint')
router.register(r'manuscript', views.ManuscriptViewSet, base_name='manuscript')

# workflow routes
router.register(r'normalized', views.NormalizedDataViewSet, base_name='normalizeddata')
router.register(r'changeset', views.ChangeSetViewSet, base_name='changeset')
router.register(r'change', views.ChangeViewSet, base_name='change')
router.register(r'raw', views.RawDataViewSet, base_name='rawdata')

urlpatterns = router.urls
