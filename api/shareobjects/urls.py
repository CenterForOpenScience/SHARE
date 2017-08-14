from rest_framework.routers import DefaultRouter

from api.shareobjects.generator import EndpointGenerator


# generate share object routes
router = DefaultRouter()
EndpointGenerator(router)
urlpatterns = router.urls
