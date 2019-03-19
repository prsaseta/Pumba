from django import forms

class MatchForm(forms.Form):
    max_players = forms.IntegerField(max_value=8, min_value=2, label = "Maximum players", initial = 4)
    title = forms.CharField(max_length= 100, min_length=1, label= "Game title", initial = "Quick match")

class FeedbackForm(forms.Form):
    email = forms.EmailField(required = False, label = "Your email (optional)", max_length = 10000)
    subject = forms.CharField(min_length = 10, label = "Subject", max_length = 1000)
    body = forms.CharField(widget = forms.Textarea, min_length = 10, label = "Text", max_length = 10000)