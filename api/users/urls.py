from django.conf.urls import url
from django.views.decorators.csrf import ensure_csrf_cookie

from rest_framework.routers import SimpleRouter

from api.users import views


router = SimpleRouter()
router.register(r'users?', views.ShareUserViewSet, base_name='user')
urlpatterns = router.urls + [
    url(r'userinfo/?', ensure_csrf_cookie(views.ShareUserView.as_view()), name='userinfo'),
]
