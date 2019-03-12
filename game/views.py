from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.cache import cache 
from game.domain_objects import *
from django.http import HttpResponseRedirect
import game.matchmaking
from game.exceptions import PumbaException
from game.forms import MatchForm
from game.models import GameKey

# Create your views here.

def index_view(request):
    return render(request, "index.html")

@login_required
def match_list2(request):
    # TODO ¿Lista de partidas en las que estás?
    # Cogemos todas las llaves de la BD
    keys = GameKey.objects.all()
    # Reconstruimos la lista de partidas
    rows = []
    for key in keys:
        g = cache.get("match_"+str(key.key))
        if g is None:
            key.delete()
            print("Borrando partida de la BD que no estaba en memoria")
            continue
        # 0: Game
        # 1: ID
        # 2: Filled
        row = []
        row.append(g)
        row.append(key.key)
        if(len(g.players) == g.maxPlayerCount):
            row.append(False)
        else:
            row.append(True)
        rows.append(row)
    error = request.GET.get("error", None)
    return render(request, "match_list.html", {"games" : rows, "error": error, "form": MatchForm()})

@login_required
def join_match(request):
    # Te une a una partida
    # Coge la ID de la partida
    id = request.GET.get("id", None)
    if (id is None):
        return HttpResponseRedirect("/game/matchmaking")
    try:
        game.matchmaking.join(request.user, id)
    except PumbaException as e:
        return HttpResponseRedirect("/game/matchmaking?error=" + str(e))
    return render(request, "game.html", {"id": id, "game_name": cache.get("match_" + id).title})

@login_required
def create_match(request):
    # Te crea una partida y te mete en ella
    if request.POST:
        form = MatchForm(request.POST)
        # Si quitas este print deja de funcionar porque ???
        print(form)
        max_players = form.cleaned_data['max_players']
        title = form.cleaned_data['title']
        user = request.user
        id = None
        try:
            id = game.matchmaking.create(max_players, user, title)
        except PumbaException as e:
            return HttpResponseRedirect("/game/matchmaking?error=" + str(e))

        return render(request, "game.html", {"id": id, "game_name": cache.get("match_" + id).title})
    else:
        return HttpResponseRedirect("/game/matchmaking")


    