from rest_framework.routers import DefaultRouter

from api import views

router = DefaultRouter()

router.register(r'normalized', views.NormalizedManuscriptViewSet, base_name='normalizedmanuscript')
router.register(r'changeset', views.ChangeSetViewSet, base_name='changeset')
router.register(r'change', views.ChangeViewSet, base_name='change')
router.register(r'person', views.PersonViewSet, base_name='person')
router.register(r'contributor', views.ContributorViewSet, base_name='contributor')
router.register(r'venue', views.VenueViewSet, base_name='venue')
router.register(r'institution', views.InstitutionViewSet, base_name='institution')
router.register(r'manuscript', views.ManuscriptViewSet, base_name='manuscript')
router.register(r'preprint', views.PreprintViewSet, base_name='preprint')
router.register(r'creative_work', views.CreativeWorkViewSet, base_name='creative_work')
router.register(r'tag', views.TagViewSet, base_name='tag')
router.register(r'taxonomy', views.TaxonomyViewSet, base_name='taxonomy')
router.register(r'award', views.AwardViewSet, base_name='award')
router.register(r'funder', views.FunderViewSet, base_name='funder')
router.register(r'raw', views.RawDataViewSet, base_name='rawdata')

urlpatterns = router.urls
