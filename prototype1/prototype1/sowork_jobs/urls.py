from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from prototype1.sowork_jobs import views

urlpatterns = [
    url(r'^$', views.JobList.as_view()),
    url(r'^/(?P<pk>[0-9a-zA-z]+)/$', views.JobDetail.as_view()),
]

urlpatterns = format_suffix_patterns(urlpatterns)
