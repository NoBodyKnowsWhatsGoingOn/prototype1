from django.conf.urls import url
from . import views
from django.contrib.auth import views as auth_views

app_name = 'sowork'
urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    # ex: /sowork/5/
    url(r'^(?P<pk>[0-9]+)/$', views.DetailView.as_view(), name='detail'),
    # ex: /sowork/5/results/
    url(r'^(?P<pk>[0-9]+)/results/$', views.ResultsView.as_view(), name='results'),
    # ex: /sowork/5/vote/
    url(r'^(?P<question_id>[0-9]+)/vote/$', views.vote, name='vote'),
    url(r'^accounts/login/$', auth_views.login),
]
