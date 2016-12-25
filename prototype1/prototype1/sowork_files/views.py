from django.http import HttpResponse
from django.http import Http404
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


def download_file(request, file_id = None):
    if file_id is None:
    	files = FileModel.objects.all()
    	return render(request, 'sowork_files/download.html', {"files": files})
    else:
    	try:
    		fileModel = FileModel.objects.get(pk=file_id)
    	except FileModel.DoesNotExist:
    		raise Http404("File of id {} does not exist".format(file_id))
    	response = HttpResponse(fileModel.file, content_type='text/plain')
    	response['Content-Disposition'] = 'attachment; filename={}'.format(fileModel.file_name)
    	return response
