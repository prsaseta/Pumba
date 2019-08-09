from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError, HttpResponseBadRequest
from authentication.forms import LoginForm, RegisterForm, RecoverPasswordRequestForm, ResetPasswordForm 
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.mail import send_mail
from authentication.models import PreRegister, RecoverPassword
from pumba.settings import IS_USING_EMAIL_VERIFICATION_FOR_REGISTRY, VERIFICATION_MAIL_URL
from django.utils.crypto import get_random_string
from django.utils.translation import gettext as _
from pumba.views import getBasicContext
from django.urls import reverse
# Create your views here.

def login_view(request):
    context = getBasicContext(request)
    # Si ya está autenticado, lo devolvemos al índice
    if (request.user.is_authenticated):
        return HttpResponseRedirect(reverse("index"))
    # Si es una petición POST, es que ha mandado usuario y contraseña para loguearse
    if request.POST:
        # Recogemos el formulario y campos
        form = LoginForm(request.POST)
        # Si el formulario no está bien relleno, redirigimos
        if not form.is_valid():
            context["form"] = form
            context["error"] = _("Your username and password didn't match. Please try again.")
            return render(request, "login.html", context)
            #return render(request, "login.html", {"form": LoginForm(), "error": _("Your username and password didn't match. Please try again.")})
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
            context["form"] = LoginForm()
            context["error"] = _("Your username and password didn't match. Please try again.")
            return render(request, "login.html", context)
            #return render(request, "login.html", {"form": LoginForm({"username": username, "password": ""}), "error": _("Your username and password didn't match. Please try again.")})
    # Si no es una petición POST, devolvemos el formulario vacío
    else:
        context["form"] = LoginForm()
        return render(request, "login.html", context)
        #return render(request, "login.html", {"form": LoginForm()})

def register_view(request):
    context = getBasicContext(request)
    # Si ya está autenticado, lo devolvemos al índice
    if (request.user.is_authenticated):
        return HttpResponseRedirect(reverse("index"))
    # Si es una petición POST, es que ha mandado datos
    if request.POST:
        # Recogemos el formulario y campos
        form = RegisterForm(request.POST)
        # Si el formulario no está bien relleno, redirigimos
        if not form.is_valid():
            context["form"] = form
            context["error"] = _("Invalid data")
            return render(request, "register.html", context)
            #return render(request, "register.html", {"form": RegisterForm(), "error": _("Invalid data")})
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        confirm = form.cleaned_data['confirm']
        email = form.cleaned_data['email']
        
        # Comprobamos que las contraseñas coincidan
        if password != confirm:
            return render(request, "register.html", {"form": form, "error": _("Passwords don't match")})
        
        # Comprobamos que el nombre de usuario no está cogido
        if User.objects.filter(username = username).count() > 0 or PreRegister.objects.filter(username = username).count() > 0:
            context["form"] = form
            context["error"] = _("That username is already taken")
            return render(request, "register.html", context)
            #return render(request, "register.html", {"form": form, "error": _("That username is already taken")})
        # Comprobamos que el nombre de usuario no es demasiado largo
        if len(username) > 32:
            context["form"] = form
            context["error"] = _("The username may only be up to 32 characters long")
            return render(request, "register.html", context)
            #return render(request, "register.html", {"form": form, "error": _("The username may only be up to 32 characters long")})
        # Comprobamos que el email no está cogido
        if User.objects.filter(email = email).count() > 0 or PreRegister.objects.filter(email = email).count() > 0:
            context["form"] = form
            context["error"] = _("That email is already taken")
            return render(request, "register.html", context)
            #return render(request, "register.html", {"form": form, "error": _("That email is already taken")})

        if IS_USING_EMAIL_VERIFICATION_FOR_REGISTRY:
            try:
                do_email_verification(username, password, email)
                return render(request, "register_confirm.html", context)
            except Exception as e:
                print(e)
                return HttpResponseRedirect(reverse("register") + "?error=" + _("There was an error while sending you the verification email, please try registering again later"))
        else:
            user = User.objects.create_user(username, email, password)
            login(request, user)
            return HttpResponseRedirect(reverse("index"))

    # Si no es una petición POST, devolvemos el formulario vacío
    else:
        context["form"] = RegisterForm()
        return render(request, "register.html", context)
        #return render(request, "register.html", {"form": RegisterForm()})

def verification_view(request):
    context = getBasicContext()
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

    return render(request, "register_success.html", context)

def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))

def do_email_verification(username, password, email):
    # Generamos la ID de verificación
    # TODO Comprobar repeticiones
    verification = get_random_string(length = 20)
    
    # Creamos el objeto de preregistro
    preregister = PreRegister(username = username, password = password, email = email, verification = verification)
    preregister.save()

    # Enviamos el correo
    url = VERIFICATION_MAIL_URL + "/authentication/verification?id=" + verification
    send_mail(_('Confirm registration at Pumba'), _('Please confirm your registration with the following link: ') + url, 'register@pumba.com', [email], fail_silently=False)

def request_password_recovery(request):
    context = getBasicContext(request)
    # Si ya está autenticado, lo devolvemos al índice
    if (request.user.is_authenticated):
        return HttpResponseRedirect("/")
    if request.POST:
        try:
            form = RecoverPasswordRequestForm(request.POST)
            if form.is_valid():
                # TODO Comprobar repeticiones
                key = get_random_string(length = 20)
                user = User.objects.get(email = form.cleaned_data["email"])
                recovery = RecoverPassword(key = key, user = user)
                recovery.save()
                url = VERIFICATION_MAIL_URL + "/authentication/reset?id=" + key
                send_mail(_('Reset password at Pumba') + ": " + user.username, _('We have received a request to reset your password. You can do so by clicking the following link: ') + url + " \n" + _("If you didn't request this change, you needn't do anything."), 'recoverypumba@pumba.com', [form.cleaned_data["email"]], fail_silently=False)
        except Exception as e:
            print(e)
        return render(request, "password_recover_request_success.html", context)
    else:
        context["form"] = RecoverPasswordRequestForm()
        return render(request, "password_recover_request.html", context)
        #return render(request, "password_recover_request.html", {"form": RecoverPasswordRequestForm()})

def reset_password(request):
    context = getBasicContext(request)
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
                context["error"] = _("Passwords don't match")
                context["form"] = ResetPasswordForm(initial={"key": key})
                return render(request, "reset_password.html", context)
                #return render(request, "reset_password.html", {"error": _("Passwords don't match"), "form": ResetPasswordForm(initial={"key": key})})
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
                return render(request, "reset_password_success.html", context)
            except Exception as e:
                print(e)
                context["error"] = _("There was an error changing your password")
                context["form"] = ResetPasswordForm(initial={"key": key})
                return render(request, "reset_password.html", context)
                #return render(request, "reset_password.html", {"error": _("There was an error changing your password"), "form": ResetPasswordForm(initial={"key": key})})
    else:
        # Comprobamos que se ha mandado la key
        key = request.GET.get("id", None)
        if key is None:
            context["error"] = _("Invalid password recovery key.")
            return render(request, "400.html", context)
            #return render(request, "400.html", {"error": _("Invalid password recovery key.")})
        # Si la key no existe, la petición no es válida
        try:
            RecoverPassword.objects.get(key = key)
        except Exception as e:
            print(e)
            context["error"] = _("Invalid password recovery key.")
            return render(request, "400.html", context)
            #return render(request, "400.html", {"error": _("Invalid password recovery key.")})
        context["form"] = ResetPasswordForm(initial={"key": key})
        return render(request, "reset_password.html", context)
        #return render(request, "reset_password.html", {"form": ResetPasswordForm(initial={"key": key})})