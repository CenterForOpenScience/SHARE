from rest_framework.routers import SimpleRouter
from api.formattedmetadatarecords import views


router = SimpleRouter()
router.register(r'formattedmetadatarecords', views.FormattedMetadataRecordViewSet, basename='formattedmetadatarecord')
urlpatterns = router.urls
