from django import forms

class PostJobForm(forms.Form):
    title = forms.CharField(label='Job Title', max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    description = forms.CharField(label='Job Description', max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    active = forms.BooleanField(required=False)