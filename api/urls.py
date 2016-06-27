from rest_framework.routers import DefaultRouter

from api.views import NormalizedManuscriptViewSet, RawDataViewSet, ChangeSetViewSet, ChangeViewSet

router = DefaultRouter()

router.register(r'normalized', NormalizedManuscriptViewSet, base_name='normalizedmanuscript')
router.register(r'changeset', ChangeSetViewSet, base_name='changeset')
router.register(r'change', ChangeViewSet, base_name='change')
router.register(r'raw', RawDataViewSet, base_name='rawdata')

urlpatterns = router.urls
