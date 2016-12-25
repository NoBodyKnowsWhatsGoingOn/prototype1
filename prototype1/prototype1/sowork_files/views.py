from django.http import HttpResponse
from django.shortcuts import render
from .forms import UploadFileForm
from .models import *

def index(request):
    return render(request, 'sowork_files/index.html')

def upload_file(request):
	if request.method == 'POST':
		print("upload_file - POST ")
		form = UploadFileForm(request.POST, request.FILES)
		if form.is_valid():
			print("upload_file - POST is_valid")
			instance = FileModel(file=request.FILES['file'], file_name="uploaded_file")
			return HttpResponse("Upload success")
	else:
		form = UploadFileForm()
	return render(request, 'sowork_files/upload.html', {'form': form})

def download_file(requst):
	return render(request, 'sowork_files/index.html')
