from rest_framework.routers import SimpleRouter
from api.formattedmetadatarecords import views


router = SimpleRouter()
router.register(r'formattedmetadatarecords', views.FormattedMetadataRecordViewSet, base_name='formattedmetadatarecord')
urlpatterns = router.urls
