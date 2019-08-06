from django import forms
from django.utils.translation import gettext_lazy as _

class LoginForm(forms.Form):
    username = forms.CharField(label = _("Username"), max_length=100)
    password = forms.CharField(label = _("Password"), widget=forms.PasswordInput)

class RegisterForm(forms.Form):
    username = forms.CharField(label = _("Username"), max_length=32)
    password = forms.CharField(label = _("Password"), widget=forms.PasswordInput)
    confirm = forms.CharField(label = _("Confirm password"), widget=forms.PasswordInput)
    email = forms.EmailField(label = _("Email"))

class RecoverPasswordRequestForm(forms.Form):
    email = forms.EmailField(label = _("Email"))

class ResetPasswordForm(forms.Form):
    key = forms.CharField(max_length=100, widget=forms.HiddenInput())
    password = forms.CharField(label = _("New password"), widget=forms.PasswordInput)
    confirmation = forms.CharField(label = _("Confirm password"), widget=forms.PasswordInput)