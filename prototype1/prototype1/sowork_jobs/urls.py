from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from . import views

urlpatterns = [
    url(r'^$', views.jobs_display, name='index'),
    url(r'^postjobs/$', views.post_jobs, name='post'),
    url(r'^update/$', views.JobList.as_view(), name=''),
    url(r'^update/(?P<job_id>[0-9a-zA-z]+)/$', views.job_detail, name='detail'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
