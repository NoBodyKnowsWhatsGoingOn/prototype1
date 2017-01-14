from django import forms

class CommentForm(forms.Form):
    body = forms.CharField(label='Comment Description', max_length=500)
    # todo: add attachments
