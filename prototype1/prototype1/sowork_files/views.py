from django.http import HttpResponse
from django.shortcuts import render
from .forms import UploadFileForm
from .models import *


def index(request):
    return render(request, 'sowork_files/index.html')


def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            instance = FileModel(file=request.FILES['file'], 
            	                 file_name=request.FILES['file'].name)
            instance.save()
            return HttpResponse("Upload success. Primary Key is {}".format(instance.id))
    else:
        form = UploadFileForm()
    return render(request, 'sowork_files/upload.html', {'form': form})


def download_file(requst):
    return render(request, 'sowork_files/index.html')
