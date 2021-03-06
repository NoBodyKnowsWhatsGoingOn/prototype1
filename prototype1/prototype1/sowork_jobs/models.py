from __future__ import unicode_literals

from django.db import models

from datetime import datetime

from django.core.urlresolvers import reverse

# Create your models here.

class JobInfo(models.Model):
    title = models.CharField(max_length=100, default="Title")
    description = models.CharField(max_length=500, default="Description")
    createTime = models.DateTimeField(editable=False)
    lastUpdateTime = models.DateTimeField(editable=False)
    active = models.BooleanField(default=False)

    def get_absolute_url(self):
        return reverse('sowork_jobs:detail', kwargs={'job_id': self.pk})

    def __str__(self): return self.title

    def save(self, *args, **kwargs):
        # On save, update timestamps
        if not self.id:
            self.createTime = datetime.utcnow() #use utc time
        self.title = self.title.replace(" ", "")
        self.lastUpdateTime = datetime.utcnow()
        return super(JobInfo, self).save(*args, **kwargs)
