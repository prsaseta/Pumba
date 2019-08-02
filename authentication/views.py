from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError, HttpResponseBadRequest
from authentication.forms import LoginForm, RegisterForm, RecoverPasswordRequestForm, ResetPasswordForm 
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.mail import send_mail
from authentication.models import PreRegister, RecoverPassword
from pumba.settings import IS_USING_EMAIL_VERIFICATION_FOR_REGISTRY, VERIFICATION_MAIL_URL
from django.utils.crypto import get_random_string
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
            return render(request, "login.html", {"form": LoginForm(), "error": "Your username and password didn't match. Please try again."})
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
            return render(request, "login.html", {"form": LoginForm({"username": username, "password": ""}), "error": "Your username and password didn't match. Please try again."})
    # Si no es una petición POST, devolvemos el formulario vacío
    else:
        return render(request, "login.html", {"form": LoginForm()})

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
        if User.objects.filter(username = username).count() > 0 or PreRegister.objects.filter(username = username).count() > 0:
            return render(request, "register.html", {"form": form, "error": "That username is already taken"})
        # Comprobamos que el nombre de usuario no es demasiado largo
        if len(username) > 32:
            return render(request, "register.html", {"form": form, "error": "The username may only be up to 32 characters long"})
        # Comprobamos que el email no está cogido
        if User.objects.filter(email = email).count() > 0 or PreRegister.objects.filter(email = email).count() > 0:
            return render(request, "register.html", {"form": form, "error": "That email is already taken"})

        if IS_USING_EMAIL_VERIFICATION_FOR_REGISTRY:
            try:
                do_email_verification(username, password, email)
                return render(request, "register_confirm.html")
            except Exception as e:
                print(e)
                return HttpResponseServerError("There was an error while sending you the verification email, please try again later")
        else:
            user = User.objects.create_user(username, email, password)
            login(request, user)
            return HttpResponseRedirect("/")

    # Si no es una petición POST, devolvemos el formulario vacío
    else:
        return render(request, "register.html", {"form": RegisterForm()})

def verification_view(request):
    # Cogemos el código de verificación
    code = request.GET.get('id', None)

    # Si no se ha mandado código, da error
    if code is None:
        return HttpResponseBadRequest("Bad request (400)")

    # Si no es un código válido, da error
    if PreRegister.objects.filter(verification = code).count() < 1:
        return HttpResponseBadRequest("Bad request (400)")

    # Confirmamos el registro
    preregister = PreRegister.objects.get(verification = code)
    user = User.objects.create_user(preregister.username, preregister.email, preregister.password)

    # Borramos el objeto de preregistro
    preregister.delete()

    return render(request, "register_success.html")

def logout_view(request):
    logout(request)
    return HttpResponseRedirect("/")

def do_email_verification(username, password, email):
    # Generamos la ID de verificación
    # TODO Comprobar repeticiones
    verification = get_random_string(length = 20)
    
    # Creamos el objeto de preregistro
    preregister = PreRegister(username = username, password = password, email = email, verification = verification)
    preregister.save()

    # Enviamos el correo
    url = VERIFICATION_MAIL_URL + "/authentication/verification?id=" + verification
    send_mail('Confirm registration at Pumba', 'Please confirm your registration with the following link: ' + url, 'register@pumba.com', [email], fail_silently=False)

def request_password_recovery(request):
    # Si ya está autenticado, lo devolvemos al índice
    if (request.user.is_authenticated):
        return HttpResponseRedirect("/")
    if request.POST:
        try:
            form = RecoverPasswordRequestForm(request.POST)
            if form.is_valid():
                # TODO Comprobar repeticiones
                key = get_random_string(length = 20)
                recovery = RecoverPassword(key = key, user = User.objects.get(email = form.cleaned_data["email"]))
                recovery.save()
                url = VERIFICATION_MAIL_URL + "/authentication/reset?id=" + key
                send_mail('Reset password at Pumba', 'We have received a request to reset your password. You can do so by clicking the following link:  ' + url + " \nIf you didn't request this change, you needn't do anything.", 'recoverypumba@pumba.com', [form.cleaned_data["email"]], fail_silently=False)
        except Exception as e:
            print(e)
        return render(request, "password_recover_request_success.html")
    else:
        return render(request, "password_recover_request.html", {"form": RecoverPasswordRequestForm()})

def reset_password(request):
    if (request.user.is_authenticated):
        logout(request)
    if request.POST:
        # Recogemos el formulario
        form = ResetPasswordForm(request.POST)
        # Comprobamos que está relleno correctamente
        if form.is_valid():
            key = form.cleaned_data["key"]
            # Si las contraseñas no coinciden:
            if form.cleaned_data["password"] != form.cleaned_data["confirmation"]:
                return render(request, "reset_password.html", {"error": "Passwords don't match", "form": ResetPasswordForm(initial={"key": key})})
            try:
                # Recuperamos el objeto de resetear contraseña
                recovery = RecoverPassword.objects.get(key = key)
                # Recuperamos el usuario
                user = recovery.user
                # Cambiamos la contraseña
                user.set_password(form.cleaned_data["password"])
                # Guardamos el usuario
                user.save()
                # Borramos el objeto de recuperar contraseña
                recovery.delete()
                return render(request, "reset_password_success.html")
            except Exception as e:
                print(e)
                return render(request, "reset_password.html", {"error": "There was an error changing your password", "form": ResetPasswordForm(initial={"key": key})})
    else:
        # Comprobamos que se ha mandado la key
        key = request.GET.get("id", None)
        if key is None:
            return render(request, "400.html", {"error": "Invalid password recovery key."})
        # Si la key no existe, la petición no es válida
        try:
            RecoverPassword.objects.get(key = key)
        except Exception as e:
            print(e)
            return render(request, "400.html", {"error": "Invalid password recovery key."})
        return render(request, "reset_password.html", {"form": ResetPasswordForm(initial={"key": key})})