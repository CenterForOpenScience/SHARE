from rest_framework.routers import DefaultRouter

from api.views import NormalizedManuscriptViewSet, RawDataViewSet

router = DefaultRouter()

router.register(r'normalized', NormalizedManuscriptViewSet, base_name='normalizedmanuscript')
router.register(r'raw', RawDataViewSet, base_name='rawdata')

urlpatterns = router.urls
