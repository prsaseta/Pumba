from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.cache import cache 
from game.domain_objects import *
from django.http import HttpResponseRedirect
import game.matchmaking
from game.exceptions import PumbaException
from game.forms import MatchForm, FeedbackForm, UserProfilePictureForm, UserProfileGameBackgroundForm
from game.models import GameKey, FeedbackMail, getUserProfile, UserProfileGameBackground, getBackgroundsAsJson
import traceback
from pumba.settings import FEEDBACK_MAIL_ADDRESS, CHEATS_ENABLED, STATIC_URL
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.urls import reverse
import json
import cloudinary.uploader
import cloudinary
import copy
from pumba.views import getBasicContext

from django.utils.translation import gettext as _

# Create your views here.

GAME_TEMPLATE = "game_phaser.html"
MATCHES_PER_PAGE = 10

def index_view(request):
    context = getBasicContext(request)
    return render(request, "index.html", context)

@login_required
def profile(request):
    context = getBasicContext(request)
    # Cogemos el usuario
    user = User.objects.get(id = request.user.id)
    # Cogemos el perfil
    profile = getUserProfile(user)
    # Hacemos un form para subir una imagen de perfil
    form = UserProfilePictureForm(initial={'profile': profile})
    # Hacemos un form para cambiar el background
    form_background = UserProfileGameBackgroundForm(instance= profile.userprofilegamebackground)
    # Añadimos datos al contexto
    context["profile"] = profile
    context["form"] = form
    context["form_background"] = form_background
    context["backgrounds"] = getBackgroundsAsJson()
    # Renderizamos el HTML
    return render(request, "profile.html", context)
    #return render(request, "profile.html", {"user": user, "profile": profile, "form": form, "form_background": form_background, "error": error, "backgrounds": getBackgroundsAsJson(), "static_path": STATIC_URL})

@login_required
def change_background(request):
    # Si se ha enviado un formulario:
    if request.POST:
        # Cogemos el usuario
        user = User.objects.get(id = request.user.id)
        # Cogemos el perfil
        profile = getUserProfile(user)
        # Cogemos el formulario
        form = UserProfileGameBackgroundForm(request.POST, instance= profile.userprofilegamebackground)
        # Comprobamos que está bien relleno
        if form.is_valid():
            # Si está intentando modificar otro perfil, se lo denegamos
            if form.cleaned_data['profile'] != profile:
                return HttpResponseRedirect(reverse("profile") + "?error=" + _("There was an error processing your request"))
            # Guardamos el nuevo fondo
            form.save()
            # Redirigimos al perfil
            return HttpResponseRedirect(reverse("profile")+ "?notification=" + _("Background changed successfully"))
        # Si ha fallado algo (normalmente hacking) redirigimos sin hacer nada
        else:
            #print(form.errors)
            return HttpResponseRedirect(reverse("profile") + "?error=" + _("There was an error processing your request"))
    # Si no se ha enviado un formulario, redirigimos y ya está
    else:
        return HttpResponseRedirect(reverse("profile"))

@login_required
def profile_picture_delete(request):
    # Cogemos el usuario
    user = User.objects.get(id = request.user.id)
    # Cogemos el perfil
    profile = getUserProfile(user)
    # Lo intentamos borrar (puede fallar por cloudinary o por no existir tal foto de perfil)
    try:
        instance = profile.userprofilepicture
        ref = copy.copy(instance.picture.public_id)
        instance.delete()
        cloudinary.uploader.destroy(ref,invalidate=True)
    # Si falla algo, notificamos
    except:
        return HttpResponseRedirect(reverse("profile") + "?error=" + _("There was an error processing your request"))
    # Si todo va bien, redirigimos
    return HttpResponseRedirect(reverse("profile"))

@login_required
def profile_picture_upload(request):
    # Comprobamos que se ha enviado un formulario
    if request.POST:
        # Cogemos el usuario actual
        user = User.objects.get(id = request.user.id)
        # Cogemos el perfil
        profile = getUserProfile(user)
        # Cogemos la instancia a actualizar (None si resulta que es la primera vez que sube imagen)
        try:
            instance = profile.userprofilepicture
            ref = copy.copy(instance.picture.public_id)
        except:
            instance = None
        # Recogemos el formulario
        # Si había una instancia de UserProfilePicture, la asociamos; si no, la creamos nueva
        if instance is None:
            form = UserProfilePictureForm(request.POST, request.FILES)
        else:
            form = UserProfilePictureForm(request.POST, request.FILES, instance=instance)
        # Validamos y limpiamos campos
        try:
            if form.is_valid():
                # Si nos intentan hackear y modificar otro perfil:
                if form.cleaned_data['profile'] != profile:
                    return HttpResponseRedirect(reverse("profile"))
                # Borramos la imagen vieja
                # try/catch porque Cloudinary puede fallar
                try:
                    if instance is not None:
                        cloudinary.uploader.destroy(ref,invalidate=True)
                except Exception as e:
                    print(e)
                    print("Could not delete image " + str(ref))
                # Guardamos el formulario, guardando la imagen nueva
                form.save()
            # Si el formulario no es válido, la imagen normalmente es el problema
            else:
                #print(form.errors)
                return HttpResponseRedirect(reverse("profile") + "?error=" + _("Could not upload image!") )
        except Exception as e:
            return HttpResponseRedirect(reverse("profile") + "?error=" + _("Could not upload image! The format is incorrect or the image is too big" ))
    # Si no se ha enviado un formulario, redirigimos
    return HttpResponseRedirect(reverse("profile"))


@login_required
def match_list3(request):
    context = getBasicContext(request)
    # Recuperamos la página que se ha pedido
    page = request.GET.get("p", 1)
    try:
        page = int(page)
    except:
        page = 1
    
    # Debug para comprobar que se ve bien el matchmaker
    debug = request.GET.get("debug", None)
    if debug is not None:
        for i in range(20):
            GameKey(key = str(i), name = "test" + str(i), max_users = 4, current_users = 0, ai_count = 0, status = "WAITING", capacity = 4).save()
            context["notification"] = "Debug matches added"
    
    # Cogemos de la BD todas las partidas en curso
    keys = GameKey.objects.all()
    # Filtramos además las partidas en las que estás metido
    user = User.objects.get(id = request.user.id)
    yours = []
    for key in keys:
        if user in key.users.all():
            yours.append(key)
    # Para hacer más fácil el template, si no estás en ninguna partida pasamos None
    if len(yours) == 0:
        yours = None
    if len(keys) == 0:
        games = None
    else:
        # Creamos el paginador
        paginator = Paginator(keys, MATCHES_PER_PAGE)
        # Cogemos la página que nos toca
        games = paginator.get_page(page)
        # Creamos la lista de páginas disponibles (porque los templates de Django son muy cortitos)
        plist = list(range(paginator.num_pages + 1))
        plist.remove(0)
        context["pages"] = plist

    # Metemos todo en el contexto
    context["games"] = games
    context["yours"] = yours
    context["form"] = MatchForm()
    context["page"] = page
    return render(request, "match_list.html", context)
    #return render(request, "match_list.html", {"games" : keys, "yours": yours, "error": error, "form": MatchForm()})

@login_required
def join_match(request):
    context = getBasicContext(request)
    # Te une a una partida
    # Coge la ID de la partida
    id = request.GET.get("id", None)
    # Si no se ha enviado ID, redirigimos a la misma página
    if (id is None):
        return HttpResponseRedirect(reverse("matchmaking") + "?error=" + _("Bad request!"))
    try:
        # Recuperamos la partida de la caché
        g = cache.get("match_"+str(id), None)
        # Si la partida ha caducado, borramos la llave
        if g is None:
            key = GameKey.objects.get(key = id)
            key.delete()
            return HttpResponseRedirect(reverse("matchmaking") + "?error=" + _("That match did not exist!"))
        # Nos unimos a la partida
        player_id = game.matchmaking.join(request.user, id)
        # Actualizamos el contexto y finalmente mandamos la página
        context["id"] = id
        context["game_name"] = g.title
        context["your_id"] = player_id
        context["cheats"] = CHEATS_ENABLED
        context["default_bg"] = getUserProfile(request.user).userprofilegamebackground.background
        return render(request, GAME_TEMPLATE, context)
        #return render(request, GAME_TEMPLATE, {"id": id, "game_name": cache.get("match_" + id).title, "your_id": player_id, 'cheats': CHEATS_ENABLED, 'default_bg': getUserProfile(request.user).userprofilegamebackground.background})
    # Salta si la llave ya estaba borrada; es lo mismo, la partida no existía
    except GameKey.DoesNotExist:
        return HttpResponseRedirect(reverse("matchmaking") + "?error=" + _("That match did not exist!"))
    # Si excepcionalmente pasa otra cosa, ponemos un error genérico
    except Exception as e:
        print(e)
        return HttpResponseRedirect("/game/matchmaking?error=" + _("There was a problem joining your match"))
    

@login_required
def create_match(request):
    context = getBasicContext(request)
    # Te crea una partida y te mete en ella
    # Comprobamos que se ha mandado el formulario
    if request.POST:
        form = MatchForm(request.POST)
        # Validamos los campos del formulario
        if form.is_valid():
            max_players = form.cleaned_data['max_players']
            ai_players = form.cleaned_data['ai_players']
            ai_difficulty = form.cleaned_data['ai_difficulty']
            title = form.cleaned_data['title']
            user = request.user
            id = None
            # Intentamos crear la partida
            try:
                id = game.matchmaking.create(max_players, user, title, ai_players, ai_difficulty)
            # Si ha habido un error creando la partida, lo mostramos (las excepciones de este método ya están pensadas
            # para poderse mostrar a un usuario)
            except ValueError as e:
                return HttpResponseRedirect(reverse("matchmaking") + "?error=" + str(e))
            # Si todo ha ido bien, enviamos la página
            context["id"] = id
            context["game_name"] = cache.get("match_" + id).title
            context["your_id"] = 0
            context["cheats"] = CHEATS_ENABLED
            context["default_bg"] = getUserProfile(request.user).userprofilegamebackground.background
            return render(request, GAME_TEMPLATE, context)
            #return render(request, GAME_TEMPLATE, {"id": id, "game_name": cache.get("match_" + id).title, "your_id": 0, 'cheats': CHEATS_ENABLED, 'default_bg': getUserProfile(request.user).userprofilegamebackground.background})
        else:
            return HttpResponseRedirect(reverse("matchmaking") + "?error=" + _("Invalid data"))
    else:
        return HttpResponseRedirect(reverse("matchmaking"))

@login_required
def feedback(request):
    context = getBasicContext(request)
    # Si está enviando el formulario:
    if request.POST:
        # Recogemos el formulario
        form = FeedbackForm(request.POST)
        # Lo ponemos bonito
        if form.is_valid():
            # Intentamos guardar el feedback en la BD
            try:
                feedback = FeedbackMail(body = form.cleaned_data["body"], email = form.cleaned_data["email"], subject = form.cleaned_data["subject"], user = request.user)
                feedback.save()
            except Exception as e:
                traceback.print_tb(e.__traceback__)
                print(e)
                context["form"] = form
                context["error"] = _("Whoops! There was an error sending your feedback. Yes, we get the irony. Please try again later.")
                return render(request, "feedback.html", context)
                #return (request, "feedback.html", {"form": form, "error": _("Whoops! There was an error sending your feedback. Yes, we get the irony. Please try again later.")})

            # Intentamos enviar un correo con el feedback
            try:
                send_mail('Feedback: ' + form.cleaned_data["subject"], "From " + form.cleaned_data["email"] + ": \n" + form.cleaned_data["body"], "feedback@pumba.com", [FEEDBACK_MAIL_ADDRESS], fail_silently=False)
            except:
                pass
            return HttpResponseRedirect("/", {"notification": _("Your feedback was sent successfully, thank you for your time!")})
        else:
            context["form"] = form
            context["error"] = _("Invalid data")
            return render(request, "feedback.html", context)
            #return render (request, "feedback.html", {"form": form, "error": "Invalid data"})
    else:
        context["form"] = FeedbackForm()
        return render(request, "feedback.html", context)
        #return render (request, "feedback.html", {"form": FeedbackForm()})
    