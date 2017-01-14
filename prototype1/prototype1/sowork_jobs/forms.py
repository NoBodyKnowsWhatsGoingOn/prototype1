from django import forms

class PostJobForm(forms.Form):
    title = forms.CharField(label='Job Title', max_length=100)
    description = forms.CharField(label='Job Description', max_length=500)
    active = forms.NullBooleanField()

