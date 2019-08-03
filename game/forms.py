from django import forms
from game.models import UserProfilePicture

class MatchForm(forms.Form):
    max_players = forms.IntegerField(max_value=6, min_value=2, label = "Maximum players", initial = 4)
    title = forms.CharField(max_length= 100, min_length=1, label= "Game title", initial = "Quick match")
    ai_players = forms.IntegerField(max_value=5, min_value=0, label = "AI players", initial = 0)
    DIFFICULTIES = (
        ("EASY", "Easy"),
        ("MEDIUM", "Medium"),
        ("HARD", "Hard")
    )
    ai_difficulty =  forms.ChoiceField(choices=DIFFICULTIES, label = "AI difficulty")

class FeedbackForm(forms.Form):
    email = forms.EmailField(required = False, label = "Your email (optional)", max_length = 10000)
    subject = forms.CharField(min_length = 10, label = "Subject", max_length = 1000)
    body = forms.CharField(widget = forms.Textarea, min_length = 10, label = "Text", max_length = 10000)

class UserProfilePictureForm(forms.ModelForm):
    class Meta:
        model = UserProfilePicture
        fields = ['picture', 'profile']
        widgets = {'profile': forms.HiddenInput(),
                    'picture': forms.FileInput(attrs={'accept': 'image/*', 'onChange': 'validateSize(this)'})}