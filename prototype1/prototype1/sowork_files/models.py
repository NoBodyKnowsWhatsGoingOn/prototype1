from __future__ import unicode_literals

from django.db import models

# Create your models here.
class FileModel(models.Model):
	file_name = models.CharField(max_length=100)
	file = models.FileField()
