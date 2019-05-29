from django.core.cache import cache 
from game.domain_objects import Player, PlayerController, GameStatus, Game
from game.exceptions import PumbaException
from django.utils.crypto import get_random_string
from game.models import GameKey
import random
# Métodos para hacer matchmaking

# Mete al usuario en partida
def join(user, match_id):
    # Recupera la partida
    game = cache.get("match_" + match_id)
    
    # Se asegura de que existe
    if (game is None):
        raise PumbaException("The match doesn't exist!")

    # Comprueba si ya está en la partida, p.e. por desconexión o lo que sea
    already_ingame = False
    for player in game.players:
        if player.controller.user == user:
            already_ingame = True
            # Le quita control a la IA
            player.controller.isAI = False
            player_id = game.players.index(player)
            return player_id
            #break
    
    if not already_ingame:
        # Se asegura de que se puede unir a la partida
        if (not (game.status is GameStatus.WAITING or game.status is GameStatus.ENDING)):
            raise PumbaException("The game is already started!")
        if(len(game.players) >= game.maxPlayerCount):
            raise PumbaException("The game is full!")

        # Actualiza la GameKey
        key = GameKey.objects.get(key = match_id)
        key.users.add(user)
        key.current_users = key.current_users + 1
        key.save()

        # Crea el controlador y el jugador y lo añade al juego
        # Se le dice que es IA porque se usa ese mismo Boolean para saber si el cliente está conectado
        # por websocket o no
        controller = PlayerController(True, user, None)
        player = Player(game, controller, user.username)
        game.players.append(player)
        game.points.append(0)

        player_id = len(game.players) - 1

        cache.set("match_" + match_id, game, None)

        # Devuelve tu ID de jugador
        return player_id

def create(max_users, host, title, ai_players = 0):
    # Crea la partida y le pone los parámetros
    game = Game()
    if(max_users < 2):
        raise ValueError("The number of users must be at least two!")
    if(max_users > 6):
        raise ValueError("The number of users cannot be more than six!")
    if (ai_players >= max_users):
        raise ValueError("Too many AIs! Are you trying to start a revolution?")
    if title is None or str(title).strip() is "":
        raise ValueError("The title cannot be empty!")
    game.maxPlayerCount = max_users
    game.host = host
    game.title = str(title).strip()
    game.aiCount = ai_players

    # Crea el jugador del host
    controller = PlayerController(True, host, None)
    player = Player(game, controller, host.username)
    game.players.append(player)
    game.points.append(0)

    # Crea los jugadores de las IAs
    for i in range(ai_players):
        ai_controller = PlayerController(True, None, None)
        ai_player = Player(game, ai_controller, getAIName())
        game.players.append(ai_player)
        game.points.append(0)
    
    # Añade la partida  a la lista
    check = "One"
    while (check is not None):
        id = get_random_string(length = 20)
        check = cache.get("match_" + id)
    cache.set("match_" + id, game, None)
    #key = GameKey(key = id, current_users = 1, max_users = max_users, name=title, ai_count = ai_players)
    #key.save()
    #key.users.add(host)
    #key.save()

    # Devuelve la ID de la partida creada
    return id
    
def getAIName():
    names = ["GLaDOS", "HAL 9000", "Felicity", "Cephalon Ordis", "Bastion", "HAN-D", "The Defect", "E.V.E", "CL4P-TP", "ATHENA", "President Eden", "EDI", "Bob", "Jane"]
    return random.choice(names)