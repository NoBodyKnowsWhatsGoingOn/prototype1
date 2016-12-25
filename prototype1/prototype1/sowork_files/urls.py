from django.conf.urls import url
from . import views

app_name = 'sowork_filesZ'
urlpatterns = [
    url(r'^$', views.index, name='index'),
] 
