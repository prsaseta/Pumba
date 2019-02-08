from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from authentication.forms import LoginForm, RegisterForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
# Create your views here.

def login_view(request):
    # Si ya está autenticado, lo devolvemos al índice
    if (request.user.is_authenticated):
        return HttpResponseRedirect("/")
    # Si es una petición POST, es que ha mandado usuario y contraseña para loguearse
    if request.POST:
        # Recogemos el formulario y campos
        form = LoginForm(request.POST)
        # Si el formulario no está bien relleno, redirigimos
        if not form.is_valid():
            return render(request, "login.html", {"form": LoginForm(), "error": True})
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        
        # Vemos si se corresponde con algún usuario
        user = authenticate(request, username=username, password=password)

        # Si existe tal usuario, lo logueamos
        if user is not None:
            login(request, user)
            return HttpResponseRedirect("/")
        # Si no, devolvemos al formulario con un error
        else:
            return render(request, "login.html", {"form": LoginForm({"username": username, "password": ""}), "error": True})
    # Si no es una petición POST, devolvemos el formulario vacío
    else:
        return render(request, "login.html", {"form": LoginForm(), "error": False})

def register_view(request):
    # Si ya está autenticado, lo devolvemos al índice
    if (request.user.is_authenticated):
        return HttpResponseRedirect("/")
    # Si es una petición POST, es que ha mandado datos
    if request.POST:
        # Recogemos el formulario y campos
        form = RegisterForm(request.POST)
        # Si el formulario no está bien relleno, redirigimos
        if not form.is_valid():
            return render(request, "register.html", {"form": RegisterForm(), "error": "Invalid data"})
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        confirm = form.cleaned_data['confirm']
        email = form.cleaned_data['email']
        
        # Comprobamos que las contraseñas coincidan
        if password != confirm:
            return render(request, "register.html", {"form": form, "error": "Passwords don't match"})
        
        # Comprobamos que el nombre de usuario no está cogido
        if User.objects.filter(username = username).count() > 0:
            return render(request, "register.html", {"form": form, "error": "That username is already taken"})
        # Comprobamos que el email no está cogido
        if User.objects.filter(email = email).count() > 0:
            return render(request, "register.html", {"form": form, "error": "That username is already taken"})

        user = User.objects.create_user(username, email, password)
        login(request, user)
        return HttpResponseRedirect("/")

    # Si no es una petición POST, devolvemos el formulario vacío
    else:
        return render(request, "register.html", {"form": RegisterForm(), "error": False})

def logout_view(request):
    logout(request)
    return HttpResponseRedirect("/")