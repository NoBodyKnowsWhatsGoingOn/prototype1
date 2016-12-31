from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from . import views

urlpatterns = [
    url(r'^$', views.jobs_display, name='index'),
    url(r'^update/$', views.JobList.as_view(),  name='post'),
    url(r'^update/(?P<pk>[0-9a-zA-z]+)/$', views.JobDetail.as_view(), name='detail'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
