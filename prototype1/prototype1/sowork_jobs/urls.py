from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from . import views

urlpatterns = [
    url(r'^$', views.jobs_display),
    url(r'^postjobs/$', views.post_jobs),
    url(r'^update/$', views.JobList.as_view()),
    url(r'^update/(?P<pk>[0-9a-zA-z]+)/$', views.JobDetail.as_view()),
]

urlpatterns = format_suffix_patterns(urlpatterns)
