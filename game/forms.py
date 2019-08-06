from django import forms
from game.models import UserProfilePicture, UserProfileGameBackground
from django.utils.translation import gettext_lazy as _

class MatchForm(forms.Form):
    max_players = forms.IntegerField(max_value=6, min_value=2, label = _("Maximum players"), initial = 4)
    title = forms.CharField(max_length= 100, min_length=1, label= _("Game title"), initial = "Quick match")
    ai_players = forms.IntegerField(max_value=5, min_value=0, label = _("AI players"), initial = 0)
    DIFFICULTIES = (
        ("EASY", _("Easy")),
        ("MEDIUM", _("Medium")),
        ("HARD", _("Hard"))
    )
    ai_difficulty =  forms.ChoiceField(choices=DIFFICULTIES, label = _("AI difficulty"))

class FeedbackForm(forms.Form):
    #error_css_class = "error"
    email = forms.EmailField(required = False, label = _("Your email (optional)"), max_length = 10000)
    subject = forms.CharField(min_length = 10, label = _("Subject"), max_length = 1000)
    body = forms.CharField(widget = forms.Textarea, min_length = 10, label = _("Text"), max_length = 10000)

class UserProfilePictureForm(forms.ModelForm):
    class Meta:
        model = UserProfilePicture
        fields = ['picture', 'profile']
        labels = {
            'picture': _('Picture'),
        }
        widgets = {'profile': forms.HiddenInput(),
                    'picture': forms.FileInput(attrs={'accept': 'image/*', 'onChange': 'validateSize(this)'})}


class UserProfileGameBackgroundForm(forms.ModelForm):
    class Meta:
        model = UserProfileGameBackground
        labels = {
            'background': _('Background'),
        }
        fields = ['background', 'profile']
        widgets = {'profile': forms.HiddenInput()}