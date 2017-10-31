from django.conf.urls import url

from api.schemas import views

schema_patterns = [
    url(r'^{}/?'.format(view.MODEL.__name__), view.as_view())
    for view in views.ModelSchemaView.model_views
]

urlpatterns = [
    url(r'^$', views.SchemaView.as_view(), name='schema'),
    url(r'^creativework/hierarchy/?$', views.ModelTypesView.as_view(), name='modeltypes'),
] + schema_patterns
