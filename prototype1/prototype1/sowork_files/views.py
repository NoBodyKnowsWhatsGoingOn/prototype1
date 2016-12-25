from django.http import HttpResponse
from django.shortcuts import render
from .forms import UploadFileForm
from .models import *

def index(request):
    return HttpResponse("Hello, world. You're at the polls index.")

def upload_file(request):
	if request.method == 'POST':
		form = UploadFileForm(request.POST, request.FILES)
		if form.is_valid():
			instance = FileModel(file=request.FILES['file'], file_name="uploaded_file")
			return HttpResponse("Upload success")
		else:
			form = UploadFileForm()
		return render(request, 'upload.html', {'form', form})
