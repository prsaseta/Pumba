from django import forms

class LoginForm(forms.Form):
    username = forms.CharField(label = "Username", max_length=100)
    password = forms.CharField(label = "Password", widget=forms.PasswordInput)

class RegisterForm(forms.Form):
    username = forms.CharField(label = "Username", max_length=100)
    password = forms.CharField(label = "Password", widget=forms.PasswordInput)
    confirm = forms.CharField(label = "Confirm password", widget=forms.PasswordInput)
    email = forms.EmailField(label = "Email")