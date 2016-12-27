from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import Http404
from prototype1.sowork_jobs.models import JobInfo
from prototype1.sowork_jobs.serializers import JobInfoSerializer
from rest_framework import status


# Create your views here.

class JobList(APIView):
    """
    List all jobs, or create a new job link.
    """
    def get(self, request, format=None):
        snippets = JobInfo.objects.all()
        serializer = JobInfoSerializer(snippets, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = JobInfoSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobDetail(APIView):
    """
    Retrieve, update or delete a job instance.
    """
    def get_object(self, pk):
        try:
            return JobInfo.objects.get(id=pk)
        except JobInfo.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        snippet = self.get_object(pk)
        serializer = JobInfoSerializer(snippet)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        snippet = self.get_object(pk)
        serializer = JobInfoSerializer(snippet, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        snippet = self.get_object(pk)
        snippet.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

