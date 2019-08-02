from django import forms

class LoginForm(forms.Form):
    username = forms.CharField(label = "Username", max_length=100)
    password = forms.CharField(label = "Password", widget=forms.PasswordInput)

class RegisterForm(forms.Form):
    username = forms.CharField(label = "Username", max_length=32)
    password = forms.CharField(label = "Password", widget=forms.PasswordInput)
    confirm = forms.CharField(label = "Confirm password", widget=forms.PasswordInput)
    email = forms.EmailField(label = "Email")

class RecoverPasswordRequestForm(forms.Form):
    email = forms.EmailField(label = "Email")

class ResetPasswordForm(forms.Form):
    key = forms.CharField(max_length=100, widget=forms.HiddenInput())
    password = forms.CharField(label = "New password", widget=forms.PasswordInput)
    confirmation = forms.CharField(label = "Confirm password", widget=forms.PasswordInput)