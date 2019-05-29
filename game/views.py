from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.cache import cache 
from game.domain_objects import *
from django.http import HttpResponseRedirect
import game.matchmaking
from game.exceptions import PumbaException
from game.forms import MatchForm, FeedbackForm
from game.models import GameKey, FeedbackMail
import traceback
from pumba.settings import FEEDBACK_MAIL_ADDRESS
from django.core.mail import send_mail
from django.contrib.auth.models import User

# Create your views here.

GAME_TEMPLATE = "game_phaser.html"

def index_view(request):
    return render(request, "index.html")

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
        return render(request, GAME_TEMPLATE, {"id": id, "game_name": cache.get("match_" + id).title, "your_id": player_id})
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
            title = form.cleaned_data['title']
            user = request.user
            id = None
            try:
                id = game.matchmaking.create(max_players, user, title, ai_players)
            except ValueError as e:
                return HttpResponseRedirect("/game/matchmaking?error=" + str(e))

            return render(request, GAME_TEMPLATE, {"id": id, "game_name": cache.get("match_" + id).title, "your_id": 0})
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
    