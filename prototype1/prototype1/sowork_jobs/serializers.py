from rest_framework import serializers
from models import JobInfo


class JobInfoSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = JobInfo
        fields = ('id', 'title', 'description', 'createTime', 'lastUpdateTime', 'active')
