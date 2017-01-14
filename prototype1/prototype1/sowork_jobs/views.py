from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import Http404
from models import JobInfo
from prototype1.comments.forms import CommentForm
from prototype1.comments.models import Comment
from serializers import JobInfoSerializer
from rest_framework import status
from django.shortcuts import render, get_object_or_404
from prototype1.sowork_jobs.forms import PostJobForm
from django.http import HttpResponseRedirect

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



def jobs_display(request):
    jobs = JobInfo.objects.all()

    return render(request, 'sowork_jobs/jobs.html', {'jobs': jobs})

def job_detail(request, job_id):
    job = get_object_or_404(JobInfo, pk=job_id)
    if request.method == 'GET':
        form = CommentForm()
    else:
        form = CommentForm(request.POST)
        if form.is_valid():
            cleaned_data = form.cleaned_data
            cleaned_data['user'] = request.user
            cleaned_data['job_info'] = job
            Comment.objects.create(**cleaned_data)

    ctx = {
        'job': job,
        'comments': job.comment_set.all().order_by('created_time'),
        'form': form
    }
    return render(request, 'sowork_jobs/job_detail.html', ctx)

def post_jobs(request):
    if request.method == 'POST':
        form = PostJobForm(request.POST)
        if form.is_valid():
            serializer = JobInfoSerializer(data=form.cleaned_data)
            if serializer.is_valid():
                serializer.save()
            return HttpResponseRedirect('/sowork_jobs/')
    else:
        form = PostJobForm()

    return render(request, 'sowork_jobs/post_jobs.html', {'form': form})
