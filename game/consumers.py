from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
import json
from django.core.cache import cache 
from game.exceptions import PumbaException
import traceback
from game.domain_objects import GameStatus, CardNumber, Suit, TurnDirection

class GameConsumer(WebsocketConsumer):
    def connect(self):
        # Si ocurre algo, rechazamos la conexión
        error = False
        # TODO ¿Hacer algo si se conecta desde dos pestañas?
        # TODO Obtener Player asociado y orden en la lista de Players
        # TODO Comprobar que la ID de la partida existe y etc

        # Cogemos el usuario autenticado
        user = None
        try:
            user = self.scope["user"]
            if user is None:
                error = True
        except:
            error = True

        # Intentamos obtener la partida
        self.match_id = self.scope['url_route']['kwargs']['match_id']
        self.match_group_name = 'match_%s' % self.match_id
        game = None
        try:
            game = cache.get(self.match_group_name)
            if game is None:
                error = True
        except:
            error = True

        # Nos aseguramos de que el usuario se supone que debe estar en la partida
        # Buscamos en la lista de jugadores y guardamos su índice
        index = None
        for i in range(len(game.players)):
            player = game.players[i]
            if player.controller.user == user:
                index = i
                break
        if index is None:
            error = True
        self.player_index = index

        if not error:
            # Se une al grupo de canales de la partida
            async_to_sync(self.channel_layer.group_add)(
                self.match_group_name,
                self.channel_name
            )
            # Enviamos notificación por chat
            notificationmsg = "User " + game.players[self.player_index].name + " joined the game"
            self.send_notification_global(notificationmsg)
            self.accept()

    def disconnect(self, close_code):
        # TODO Darle control a la IA
        # TODO Borrar la partida si no quedan usuarios
        game = cache.get(self.match_group_name)
        username = game.players[self.player_index].name
        # Avisamos al resto de jugadores
        notificationmsg = "User " + username + " disconnected from the game"
        self.send_notification_global(notificationmsg)
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.match_group_name,
            self.channel_name
        )

    # Recibe mensajes del websocket
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        pkgtype = text_data_json['type']

        game = cache.get(self.match_group_name)
        username = game.players[self.player_index].name

        # Procesamiento cuando recibe un mensaje de chat
        if pkgtype == "chat_message":
            # Reenvía mensaje de chat a todos los canales, incluyéndose a sí mismo
            # El "type" indica qué método ejecutar de los consumidores que reciban el mensaje
            # Cuidado: el type no significa lo mismo mandándoselo al grupo que mandándoselo al cliente
            # En el grupo dice método a ejecutar, en cliente indica tipo de mensaje
            message = text_data_json['message']
            async_to_sync(self.channel_layer.group_send)(
                self.match_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'username': username
                }
            )
        # Procesamiento de orden "empezar partida"
        elif pkgtype == "begin_match":
            try:
                # Comprueba que es el host
                user = self.scope["user"]
                if game.host.id is not user.id:
                    raise PumbaException("You are not the host!")
                else:
                    # Hace el procesamiento de empezar la partida
                    game.begin_match()
                    cache.set("match_" + self.match_id, game, None)
                    # Le da el OK
                    self.send_ok()
                    # Notifica a todos
                    self.send_notification_global("The match has begun!")
            except PumbaException as e:
                self.send_error_msg(e)
            except Exception as e:
                self.send_error_msg_generic(e)
        elif pkgtype == "begin_turn":
            try:
                # Comprueba que es su turno
                if self.player_index is not game.currentPlayer:
                    raise PumbaException("It's not your turn!")
                # Intenta terminar el turno
                game.begin_turn()
                cache.set("match_" + self.match_id, game, None)
                # Le da el OK
                self.send_ok()
                # Notifica a todos
                self.send_notification_global("Player " + username + " ends their turn")
            except PumbaException as e:
                self.send_error_msg(e)
            except Exception as e:
                self.send_error_msg_generic(e)
        elif pkgtype == "game_state":
            self.send_game_state()
                
    # Imprime en pantalla la stack trace y devuelve un mensaje de error al cliente actual
    def send_error_msg(self, exception):
        traceback.print_tb(exception.__traceback__)
        self.send(text_data=json.dumps({
            'type': 'chat_error',
            'message': str(exception),
        }))

    def send_error_msg_generic(self, exception):
        traceback.print_tb(exception.__traceback__)
        self.send(text_data=json.dumps({
            'type': 'chat_error',
            'message': "An unexpected server error ocurred",
        }))

    # Le envía un mensaje de OK al cliente actual
    def send_ok(self):
        self.send(text_data=json.dumps({
            'type': 'ok'
        }))

    # Envía el estado de juego al cliente actual
    def send_game_state(self, curgame = None):
        # Recupera el estado de juego
        if curgame is None:
            game = cache.get(self.match_group_name)
        else:
            game = curgame
        # Recupera las cartas de la mano
        cards = game.players[self.player_index].hand
        hand = []
        # Las transforma a un formato más cómodo
        for card in cards:
            hand.append([Suit(card.suit).name, CardNumber(card.number).name])

        # Sustituye estos campos si no tienen valor
        lastnumber = None
        lastsuit = None
        lasteffect = None
        turndir = None
        if game.lastNumber is None:
            lastnumber = "None"
        else:
            lastnumber = CardNumber(game.lastNumber).name,
        if game.lastSuit is None:
            lastsuit = "None"
        else:
            lastsuit = Suit(game.lastSuit).name,
        if game.lastEffect is None:
            lasteffect = "None"
        else:
            lasteffect = CardNumber(game.lastEffect).name,
        if game.turnDirection is None:
            turndir = "None"
        else:
            turndir = TurnDirection(game.turnDirection).name,


        self.send(text_data=json.dumps({
            'type': 'game_state',
            'game_status': GameStatus(game.status).name,
            'last_suit': lastsuit,
            'last_number': lastnumber,
            'last_effect': lasteffect,
            'current_player': game.currentPlayer,
            'next_player': game.nextPlayer,
            'turn_direction': turndir,
            'draw_counter': game.drawCounter,
            'draw_pile': len(game.drawPile),
            'play_pile': len(game.playPile),
            'hand': hand
        }))
    
    # Envía un mensaje de notificación a todos los clientes
    def send_notification_global(self, text):
        async_to_sync(self.channel_layer.group_send)(
            self.match_group_name,
            {
                'type': 'chat_notification',
                'message': text
            }
        )

    # Replica mensaje de chat de usuario
    def chat_message(self, event):
        message = event['message']
        username = event['username']

        # Send message to WebSocket
        self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message,
            'username': username
        }))

    # Envía una notificación de chat
    def chat_notification(self, event):
        # Recupera el mensaje
        message = event['message']

        # Envía el mensaje al websocket en cliente
        self.send(text_data=json.dumps({
            'type': 'chat_notification',
            'message': message
        }))