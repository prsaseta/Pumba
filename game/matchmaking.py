from django.core.cache import cache 
from game.domain_objects import Player, PlayerController, GameStatus, Game
from game.exceptions import PumbaException
from django.utils.crypto import get_random_string
from game.models import GameKey
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
            break
    
    if not already_ingame:
        # Se asegura de que se puede unir a la partida
        if (game.status is not GameStatus.WAITING):
            raise PumbaException("The game is already started!")
        if(len(game.players) >= game.maxPlayerCount):
            raise PumbaException("The game is full!")

        # Crea el controlador y el jugador y lo añade al juego
        # Se le dice que es IA porque se usa ese mismo Boolean para saber si el cliente está conectado
        # por websocket o no
        controller = PlayerController(True, user, None)
        player = Player(game, controller, user.username)
        game.players.append(player)

        cache.set("match_" + match_id, game, None)

def create(max_users, host, title):
    # Crea la partida y le pone los parámetros
    game = Game()
    if(max_users < 2):
        raise ValueError("The number of users must be at least two!")
    if(max_users > 8):
        raise ValueError("The number of users cannot be more than eight!")
    if title is None or str(title).strip() is "":
        raise ValueError("The title cannot be empty!")
    game.maxPlayerCount = max_users
    game.host = host
    game.title = str(title).strip()

    # Crea el jugador del host
    controller = PlayerController(True, host, None)
    player = Player(game, controller, host.username)
    game.players.append(player)
    
    # Añade la partida  a la lista
    check = "One"
    while (check is not None):
        id = get_random_string(length = 20)
        check = cache.get("match_" + id)
    cache.set("match_" + id, game, None)
    key = GameKey(key = id)
    key.save()

    # Devuelve la ID de la partida creada
    return id
    
