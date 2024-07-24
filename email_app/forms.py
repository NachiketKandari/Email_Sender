from django import forms

class EmailForm(forms.Form):
    email_file = forms.FileField()
    subject = forms.CharField(max_length=255)
    body = forms.CharField(widget=forms.Textarea, help_text="Use {name} to insert the recipient's name and {company} to insert the company name.")
