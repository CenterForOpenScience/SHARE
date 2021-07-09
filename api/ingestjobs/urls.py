from rest_framework.routers import SimpleRouter
from api.ingestjobs import views


router = SimpleRouter()
router.register(r'ingestjobs', views.IngestJobViewSet, basename='ingestjob')
urlpatterns = router.urls
