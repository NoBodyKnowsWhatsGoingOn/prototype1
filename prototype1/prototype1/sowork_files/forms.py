from django.forms import ModelForm
from .models import * 

class UploadFileForm(ModelForm):
	class Meta:
		model = FileModel
		fields = ['file']

