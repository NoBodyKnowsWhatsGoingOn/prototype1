from rest_framework import serializers
from prototype1.sowork_jobs.models import JobInfo


class JobInfoSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = JobInfo
        fields = ('id', 'title', 'description', 'createTime', 'lastUpdateTime', 'active')
