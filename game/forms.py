from django import forms

class MatchForm(forms.Form):
    max_players = forms.IntegerField(max_value=8, min_value=2, label = "Maximum players", initial = 4)
    title = forms.CharField(max_length= 100, min_length=1, label= "Game title", initial = "Quick match")