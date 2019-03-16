from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
import json
from django.core.cache import cache 
from game.exceptions import PumbaException
import traceback
from game.domain_objects import GameStatus, CardNumber, Suit, TurnDirection, ActionType

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

        # Si ya está conectado en otra pestaña no le dejamos
        if not game.players[self.player_index].controller.isAI:
            print("Entra en el if")
            print(error)
            error = True

        if not error:
            print("Debería aceptar conexión")
            # Anotamos que el jugador está online
            game.players[self.player_index].controller.isAI = False
            cache.set("match_" + self.match_id, game, None)
            # Se une al grupo de canales de la partida
            async_to_sync(self.channel_layer.group_add)(
                self.match_group_name,
                self.channel_name
            )
            # Enviamos notificación por chat
            notificationmsg = "User " + game.players[self.player_index].name + " joined the game"
            self.send_notification_global(notificationmsg)
            self.was_connected_successfully_to_game = True
            self.accept()
        else:
            self.was_connected_successfully_to_game = False

    def disconnect(self, close_code):
        if self.was_connected_successfully_to_game:
            # Cogemos la partida
            game = cache.get(self.match_group_name)
            # Anotamos que el jugador está desconectado
            game.players[self.player_index].controller.isAI = True
            # Avisamos al resto de jugadores
            username = game.players[self.player_index].name
            notificationmsg = "User " + username + " disconnected from the game"
            self.send_notification_global(notificationmsg)
            
            # Si todos los usuarios se desconectan, borramos la partida
            anyone_connected = False
            for player in game.players:
                if player.controller.isAI == False:
                    anyone_connected = True
                    
            if not anyone_connected:
                cache.set("match_" + self.match_id, None, 1)
            else:
                cache.set("match_" + self.match_id, game, None)
        
        # Dejamos el canal
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
                    # Actualiza el estado de todos
                    self.send_game_state_global()
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
                # Actualiza el estado de todos
                self.send_game_state_global()
            except PumbaException as e:
                self.send_error_msg(e)
            except Exception as e:
                self.send_error_msg_generic(e)
        elif pkgtype == "game_state":
            self.send_game_state()
        elif pkgtype == "draw_card":
            try:
                # Comprueba que es su turno
                if self.player_index is not game.currentPlayer:
                    raise PumbaException("It's not your turn!")
                # Intenta robar carta
                # Cambia la acción dependiendo si hay contador de robo o no
                forced_draw = None
                if game.drawCounter > 0:
                    forced_draw = game.drawCounter
                    game.player_action_draw_forced()
                else:
                    game.player_action_draw()
                cache.set("match_" + self.match_id, game, None)
                # Le da el OK
                self.send_ok()
                # Notifica a todos
                if forced_draw is not None:
                    self.send_notification_global("Player " + username + " draws " + str(forced_draw) + " cards and resets the counter")
                else:
                    self.send_notification_global("Player " + username + " draws a card")
                # Actualiza el estado de todos
                self.send_game_state_global()
            except PumbaException as e:
                self.send_error_msg(e)
            except Exception as e:
                self.send_error_msg_generic(e)
        elif pkgtype == "play_card":
            try:
                # Comprueba que es su turno
                if self.player_index is not game.currentPlayer:
                    raise PumbaException("It's not your turn!")
                # Recupera la carta que quiere jugar
                index = int(text_data_json['index'])
                card = game.players[self.player_index].hand[index]
                # Intenta jugar la carta
                game.player_action_play(index)
                cache.set("match_" + self.match_id, game, None)
                # Le da el OK
                self.send_ok()
                # Notifica a todos
                self.send_notification_global("Player " + username + " plays " + CardNumber(card.number).name + " of " + Suit(card.suit).name)
                # Envía el efecto de DIVINE si se aplica
                if card.number is CardNumber.DIVINE and not game.turn.has(ActionType.PLAYKING):
                    if len(game.drawPile) > 0:
                        top = game.drawPile[len(game.drawPile) - 1]
                        self.send(text_data=json.dumps({
                            'type': 'chat_notification',
                            'message': "The next drawn card will be a " + CardNumber(top.number).name + " of " + Suit(top.suit).name
                        }))
                    else:
                        self.send(text_data=json.dumps({
                        'type': 'chat_notification',
                        'message': "The draw pile is empty, so you can't divine it"
                    }))
                # Comprueba si se ha ganado la partida
                if len(game.players[self.player_index].hand) == 0:
                    self.send_notification_global("Player " + username + " wins the match!")
                    # TODO Actualiza el estado de juego y etc
                    game.status = GameStatus.ENDING
                    cache.set("match_" + self.match_id, game, None)
                # Actualiza el estado de todos
                self.send_game_state_global()
            except PumbaException as e:
                self.send_error_msg(e)
            except Exception as e:
                self.send_error_msg_generic(e)
        elif pkgtype == "switch_effect":
            try:
                # Comprueba que es su turno
                if self.player_index is not game.currentPlayer:
                    raise PumbaException("It's not your turn!")
                # Intenta hacer el efecto
                game.player_action_switch(Suit[text_data_json['switch']])
                cache.set("match_" + self.match_id, game, None)
                # Le da el OK
                self.send_ok()
                # Notifica a todos
                self.send_notification_global("Player " + username + " changes the current suit to " + Suit[text_data_json['switch']].name)
                # Actualiza el estado de todos
                self.send_game_state_global()
            except PumbaException as e:
                self.send_error_msg(e)
            except Exception as e:
                self.send_error_msg_generic(e)

                
    # Imprime en pantalla la stack trace y devuelve un mensaje de error al cliente actual
    def send_error_msg(self, exception):
        traceback.print_tb(exception.__traceback__)
        self.send(text_data=json.dumps({
            'type': 'chat_error',
            'message': str(exception),
        }))

    def send_error_msg_generic(self, exception):
        traceback.print_tb(exception.__traceback__)
        print(exception)
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
    def send_game_state(self, event = None, curgame = None):
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

        # Lista de jugadores
        # 0: Nickname
        # 1: Cartas en la mano
        # 2: Estado de conexión (Conectado, IA)
        players = []
        for player in game.players:
            players.append([player.name, len(player.hand), player.controller.isAI])


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
            'hand': hand,
            'players': players
        }))
    
    # Envía el nuevo estado de juego a todos los jugadores conectados
    def send_game_state_global(self):
        async_to_sync(self.channel_layer.group_send)(
            self.match_group_name,
            {
                'type': 'send_game_state'
            }
        )
    
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