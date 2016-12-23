from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
# Create your views here.
from django.template import loader
from django.urls import reverse
from django.utils import timezone
from django.views.generic import ListView, UpdateView, DetailView
from django.contrib.auth.decorators import login_required
from .models import Question, Choice

class IndexView(LoginRequiredMixin, ListView):
    template_name = 'sowork/index.html'
    context_object_name = 'latest_question_list'
    def get_queryset(self):
        return Question.objects.filter(
            pub_date__lte=timezone.now()
        ).order_by('-pub_date')[:5]

class DetailView(LoginRequiredMixin, DetailView):
    template_name = 'sowork/detail.html'
    model = Question
    def get_queryset(self):
        return Question.objects.filter(
            pub_date__lte=timezone.now()
        )

class ResultsView(DetailView):
    template_name = 'sowork/results.html'
    model = Question
# def index(request):
#     latest_question_list = Question.objects.order_by('-pub_date')[:5]
#     template = loader.get_template('sowork/index.html')
#     context = {
#         'latest_question_list': latest_question_list,
#     }
#     return render(request, 'sowork/index.html', context)

# def detail(request, question_id):
#     question = get_object_or_404(Question, pk=question_id)
#     return render(request, 'sowork/detail.html', {'question': question})
#
# def results(request, question_id):
#     question = get_object_or_404(Question, pk=question_id)
#     return render(request, 'sowork/results.html', {'question': question})
@login_required()
def vote(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    try:
        selected_choice = question.choice_set.get(pk=request.POST['choice'])
    except (KeyError, Choice.DoesNotExist):
        return render(request, 'sowork/detail.html',{
            'question':question,
            "error_message":"Please select one option to vote",
        })
    else:
        selected_choice.votes += 1
        selected_choice.save();
        return HttpResponseRedirect(reverse('sowork:results', args=(question_id)))
