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
from django.contrib.auth.models import User
from django.urls import reverse
import json
import cloudinary.uploader
import cloudinary
import copy

# Create your views here.

GAME_TEMPLATE = "game_phaser.html"

def index_view(request):
    return render(request, "index.html")

@login_required
def profile(request):
    # Cogemos el usuario
    user = User.objects.get(id = request.user.id)
    # Cogemos el perfil
    profile = getUserProfile(user)
    # Hacemos un form para subir una imagen de perfil
    form = UserProfilePictureForm(initial={'profile': profile})
    # Hacemos un form para cambiar el background
    form_background = UserProfileGameBackgroundForm(instance= profile.userprofilegamebackground)
    # Renderizamos el HTML
    error = request.GET.get("error", None)
    return render(request, "profile.html", {"user": user, "profile": profile, "form": form, "form_background": form_background,
     "error": error, "backgrounds": getBackgroundsAsJson(), "static_path": STATIC_URL})

@login_required
def change_background(request):
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
                print("Los profiles no coinciden")
                return HttpResponseRedirect(reverse("profile") + "?error=" + "There was an error processing your request")
            form.save()
            return HttpResponseRedirect(reverse("profile"))
        else:
            print(form.errors)
            return HttpResponseRedirect(reverse("profile") + "?error=" + "There was an error processing your request")
    else:
        return HttpResponseRedirect(reverse("profile"))

@login_required
def profile_picture_delete(request):
    # Cogemos el usuario
    user = User.objects.get(id = request.user.id)
    # Cogemos el perfil
    profile = getUserProfile(user)
    try:
        instance = profile.userprofilepicture
        ref = copy.copy(instance.picture.public_id)
        instance.delete()
        cloudinary.uploader.destroy(ref,invalidate=True)
    except:
        pass

    return HttpResponseRedirect(reverse("profile"))

@login_required
def profile_picture_upload(request):
    if request.POST:
        # Cogemos el usuario
        user = User.objects.get(id = request.user.id)
        # Cogemos el perfil
        profile = getUserProfile(user)
        # Cogemos la instancia a actualizar
        try:
            instance = profile.userprofilepicture
            ref = copy.copy(instance.picture.public_id)
        except:
            instance = None
        # Recogemos el formulario
        if instance is None:
            form = UserProfilePictureForm(request.POST, request.FILES)
        else:
            form = UserProfilePictureForm(request.POST, request.FILES, instance=instance)
        # Validamos y limpiamos campos
        try:
            if form.is_valid():
                if form.cleaned_data['profile'] != profile:
                    print("Los profiles no coinciden")
                    return HttpResponseRedirect(reverse("profile"))
                # Borramos la imagen vieja
                try:
                    if instance is not None:
                        cloudinary.uploader.destroy(ref,invalidate=True)
                except Exception as e:
                    print(e)
                    print("Could not delete image " + str(ref))
                # Guardamos el formulario
                form.save()
            else:
                print(form.errors)
                return HttpResponseRedirect(reverse("profile") + "?error=" + "Could not upload image!" )
        except Exception as e:
            return HttpResponseRedirect(reverse("profile") + "?error=" + "Could not upload image! The format is incorrect or the image is too big" )
        
    return HttpResponseRedirect(reverse("profile"))


@login_required
def match_list3(request):
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
        keys = None
    error = request.GET.get("error", None)
    return render(request, "match_list.html", {"games" : keys, "yours": yours, "error": error, "form": MatchForm()})

@login_required
def join_match(request):
    # Te une a una partida
    # Coge la ID de la partida
    id = request.GET.get("id", None)
    if (id is None):
        return HttpResponseRedirect("/game/matchmaking")
    try:
        g = cache.get("match_"+str(id), None)
        if g is None:
            key = GameKey.objects.get(key = id)
            key.delete()
            return HttpResponseRedirect("/game/matchmaking?error=" + "That match did not exist!")
        player_id = game.matchmaking.join(request.user, id)
        return render(request, GAME_TEMPLATE, {"id": id, "game_name": cache.get("match_" + id).title, "your_id": player_id, 'cheats': CHEATS_ENABLED, 'default_bg': getUserProfile(request.user).userprofilegamebackground.background})
    except Exception as e:
        return HttpResponseRedirect("/game/matchmaking?error=" + str(e))
    

@login_required
def create_match(request):
    # Te crea una partida y te mete en ella
    if request.POST:
        form = MatchForm(request.POST)
        # Si quitas este print deja de funcionar porque ???
        #print(form)
        if form.is_valid():
            max_players = form.cleaned_data['max_players']
            ai_players = form.cleaned_data['ai_players']
            ai_difficulty = form.cleaned_data['ai_difficulty']
            title = form.cleaned_data['title']
            user = request.user
            id = None
            try:
                id = game.matchmaking.create(max_players, user, title, ai_players, ai_difficulty)
            except ValueError as e:
                return HttpResponseRedirect("/game/matchmaking?error=" + str(e))

            return render(request, GAME_TEMPLATE, {"id": id, "game_name": cache.get("match_" + id).title, "your_id": 0, 'cheats': CHEATS_ENABLED, 'default_bg': getUserProfile(request.user).userprofilegamebackground.background})
        else:
            return HttpResponseRedirect("/game/matchmaking?error=" + str(e))
    else:
        return HttpResponseRedirect("/game/matchmaking")

@login_required
def feedback(request):
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
                return (request, "feedback.html", {"form": FeedbackForm, "error": "Whoops! There was an error sending your feedback. Yes, we get the irony. Please try again later."})

            # Intentamos enviar un correo con el feedback
            try:
                send_mail('Feedback: ' + form.cleaned_data["subject"], "From " + form.cleaned_data["email"] + ": \n" + form.cleaned_data["body"], "feedback@pumba.com", [FEEDBACK_MAIL_ADDRESS], fail_silently=False)
            except:
                pass
            
            return HttpResponseRedirect("/", {"notification": "Your feedback was sent successfully, thank you for your time!"})
        else:
            return render (request, "feedback.html", {"form": FeedbackForm, "error": "Invalid data"})
    else:
        return render (request, "feedback.html", {"form": FeedbackForm})
    