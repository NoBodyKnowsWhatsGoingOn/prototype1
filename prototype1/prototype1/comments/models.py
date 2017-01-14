from django.db import models

from prototype1.accounts.models import MyProfile
from prototype1.sowork_jobs.models import JobInfo
from django.utils.translation import ugettext as _
from prototype1.users.models import User
from datetime import datetime

class Comment(models.Model):
    user = models.ForeignKey(User, verbose_name=_('user'))
    body = models.TextField('comment')
    created_time = models.DateTimeField('post_time', auto_now_add=True)
    job_info = models.ForeignKey(JobInfo, verbose_name='job', on_delete=models.CASCADE)

    def __str__(self):
        return self.body[:20]

    def save(self, *args, **kwargs):
        # On save, update timestamps
        if not self.id:
            self.created_time = datetime.utcnow() #use utc time
        self.created_time = datetime.utcnow()
        return super(Comment, self).save(*args, **kwargs)
