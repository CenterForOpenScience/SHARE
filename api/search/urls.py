from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from api.search import views


urlpatterns = [
    path(
        # sharev2 back-compat
        r'creativeworks/_search',
        csrf_exempt(views.Sharev2ElasticSearchView.as_view()),
        name='search'
    ),
]
