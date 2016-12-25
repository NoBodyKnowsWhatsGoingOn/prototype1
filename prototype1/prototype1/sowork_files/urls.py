from django.conf.urls import url
from . import views

app_name = 'sowork_files'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^upload/', views.upload_file, name='upload_file'),
    url(r'^download/', views.download_file, name='download_file'),
] 
