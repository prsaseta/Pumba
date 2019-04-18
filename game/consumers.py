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
        self.disconnected_by_substitute = False

        # TODO Revisar la lógica de desconexión y borrado de partidas

        # Cogemos el usuario autenticado
        user = None
        try:
            user = self.scope["user"]
            if user is None:
                error = True
        except:
            error = True

        self.user_id = user.id

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
        # Desconecta el otro consumidor (si lo hay) y nos conectamos nosotros
        # El self.close() ejecuta disconnect.
        if not game.players[self.player_index].controller.isAI:
            async_to_sync(self.channel_layer.group_send)(
                self.match_group_name,
                {
                    'type': 'substitute_disconnect',
                    'user_id': self.user_id
                }
            )
            #error = True

        if not error:
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
            # TODO Comprobar si hay consumidores que no respondan pero sus jugadores aparezcan
            # conectados y desconectarlos.
        else:
            self.was_connected_successfully_to_game = False
            #self.close()

    def substitute_disconnect(self, event):
        user_id = event['user_id']
        if user_id is self.user_id:
            # Cuando se conecta el usuario abriendo un websocket nuevo, cerramos el viejo
            # Se avisa al cliente
            self.send(text_data=json.dumps({
                'type': 'notification',
                'message': "You opened the game on another window; closing this one"
            }))
            # Dejamos el canal
            self.disconnected_by_substitute = True
            self.close()


    def disconnect(self, close_code):
        if self.was_connected_successfully_to_game and not self.disconnected_by_substitute:
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

        # Ejecuta el procesamiento necesario dependiendo del tipo de comando enviado
        if pkgtype == "chat_message":
            self.trigger_chat_message(text_data_json['message'], username)
        elif pkgtype == "begin_match":
            self.trigger_begin_match()
        elif pkgtype == "begin_turn":
            self.trigger_begin_turn()
        elif pkgtype == "game_state":
            self.send_game_state()
        elif pkgtype == "draw_card":
            self.trigger_draw_card()
        elif pkgtype == "play_card":
            self.trigger_play_card(text_data_json['index'])
        elif pkgtype == "switch_effect":
            self.trigger_switch_effect(text_data_json['switch'])

    def trigger_chat_message(self, text, username):
        # Reenvía mensaje de chat a todos los canales, incluyéndose a sí mismo
        # El "type" indica qué método ejecutar de los consumidores que reciban el mensaje
        # Cuidado: el type no significa lo mismo mandándoselo al grupo que mandándoselo al cliente
        # En el grupo dice método a ejecutar, en cliente indica tipo de mensaje
        async_to_sync(self.channel_layer.group_send)(
            self.match_group_name,
            {
                'type': 'chat_message',
                'message': text,
                'username': username
            }
        )

    def trigger_begin_match(self):
        # Se ejecuta cuando se intenta empezar una partida
        # Debe de haber al menos dos jugadores y la partida estar parada
        try:
            # Recupera la partida
            game = cache.get(self.match_group_name)
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
                # Actualiza el estado de todos
                self.send_game_state_global({"type": "begin_match"})
        except PumbaException as e:
            self.send_error_msg(e)
        except Exception as e:
            self.send_error_msg_generic(e)

    def trigger_begin_turn(self):
        try:
            # Recupera la partida
            game = cache.get(self.match_group_name)
            username = game.players[self.player_index].name
            # Comprueba que es su turno
            if self.player_index is not game.currentPlayer:
                raise PumbaException("It's not your turn!")
            # Intenta terminar el turno
            game.begin_turn()
            cache.set("match_" + self.match_id, game, None)
            # Le da el OK
            self.send_ok()
            # Actualiza el estado de todos
            self.send_game_state_global({"type": "end_turn", "player": username})
            # Si el siguiente jugador es una IA, que haga cosas de IA
            # TODO No se envían los game states bien cuando los envía la IA
            # O bien que el send_game_state_global envíe opcionalmente el game actual o bien
            # decirle al frontend que ignore los estados de la IA (apaño mierder)
            # TODO Si la IA no puede robar cartas porque no hay cartas en la pila se queda pillada
            while game.players[game.currentPlayer].controller.isAI:
                ai_player = game.players[game.currentPlayer]
                ai_hand = game.players[game.currentPlayer].hand
                # Si hay contador de robo, o refleja o roba.
                if game.drawCounter > 0:
                    needs_draw = True
                    for i in range(len(ai_hand)):
                        card = ai_hand[i]
                        if card.number is CardNumber.ONE or card.number is CardNumber.TWO:
                            game.player_action_play(i)
                            self.send_game_state_global({"type": "play_card", "player": ai_player.name, "card": {"suit": Suit(card.suit).name, "number": CardNumber(card.number).name}})
                            game.begin_turn()
                            cache.set("match_" + self.match_id, game, None)
                            self.send_game_state_global({"type": "end_turn", "player": ai_player.name, "ai": True})
                            needs_draw = False
                            break
                    if (needs_draw):
                        forced_draw = game.drawCounter
                        game.player_action_draw_forced()
                        self.send_game_state_global({"type": "draw_card_forced", "player": ai_player.name, "number": forced_draw})
                        game.begin_turn()
                        cache.set("match_" + self.match_id, game, None)
                        self.send_game_state_global({"type": "end_turn", "player": ai_player.name})
                # Si no hay contador de robo:
                else:
                    # Busca una carta cualquiera que jugar
                    cannot_play = True
                    for i in range(len(ai_hand)):
                        card = ai_hand[i]
                        if card.suit is game.lastSuit or card.number is game.lastNumber:
                            cannot_play = False
                            game.player_action_play(i)
                            self.send_game_state_global({"type": "play_card", "player": ai_player.name, "card": {"suit": Suit(card.suit).name, "number": CardNumber(card.number).name}})
                            game.begin_turn()
                            cache.set("match_" + self.match_id, game, None)
                            self.send_game_state_global({"type": "end_turn", "player": ai_player.name})
                            break
                    # Si no puede jugar ninguna, roba dos cartas y termina su turno
                    if cannot_play:
                        game.player_action_draw()
                        self.send_game_state_global({"type": "draw_card", "player": ai_player.name})
                        game.player_action_draw()
                        self.send_game_state_global({"type": "draw_card", "player": ai_player.name})
                        game.begin_turn()
                        cache.set("match_" + self.match_id, game, None)
                        self.send_game_state_global({"type": "end_turn", "player": ai_player.name})
                cache.set("match_" + self.match_id, game, None)
                self.send_game_state_global()
        except PumbaException as e:
            self.send_error_msg(e)
        except Exception as e:
            self.send_error_msg_generic(e)

    def trigger_draw_card(self):
        try:
            # Recupera la partida
            game = cache.get(self.match_group_name)
            username = game.players[self.player_index].name
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
            # Actualiza a todos
            if forced_draw is not None:
                self.send_game_state_global({"type": "draw_card_forced", "player": username, "number": forced_draw})
            else:
                self.send_game_state_global({"type": "draw_card", "player": username})
        except PumbaException as e:
            self.send_error_msg(e)
        except Exception as e:
            self.send_error_msg_generic(e)

    def trigger_play_card(self, index):
        try:
            # Recupera la partida
            game = cache.get(self.match_group_name)
            username = game.players[self.player_index].name
            # Comprueba que es su turno
            if self.player_index is not game.currentPlayer:
                raise PumbaException("It's not your turn!")
            # Recupera la carta que quiere jugar
            index = int(index)
            card = game.players[self.player_index].hand[index]
            # Intenta jugar la carta
            game.player_action_play(index)
            cache.set("match_" + self.match_id, game, None)
            # Le da el OK
            self.send_ok()
            # Envía el efecto de DIVINE si se aplica
            if (card.number is CardNumber.DIVINE and not game.turn.has(ActionType.PLAYKING)) or (card.number is CardNumber.COPY and game.lastEffect is CardNumber.DIVINE):
                if len(game.drawPile) > 0:
                    top = game.drawPile[len(game.drawPile) - 1]
                    self.send(text_data=json.dumps({
                        'type': 'divination',
                        'card': {"number": CardNumber(top.number).name, "suit": Suit(top.suit).name}
                    }))
                else:
                    self.send(text_data=json.dumps({
                    'type': 'divination',
                    'card': None
                }))
            # Actualiza el estado de todos
            self.send_game_state_global(self.send_game_state_global({"type": "play_card", "player": username, "card": {"suit": Suit(card.suit).name, "number": CardNumber(card.number).name}}))
            # Comprueba si se ha ganado la partida
            if len(game.players[self.player_index].hand) == 0:
                self.send_game_state_global(self.send_game_state_global({"type": "game_won", "player": username}))
                game.status = GameStatus.ENDING
                cache.set("match_" + self.match_id, game, None)
        except PumbaException as e:
            self.send_error_msg(e)
        except Exception as e:
            self.send_error_msg_generic(e)
    
    def trigger_switch_effect(self, suit):
        try:
            # Recupera la partida
            game = cache.get(self.match_group_name)
            username = game.players[self.player_index].name
            # Comprueba que es su turno
            if self.player_index is not game.currentPlayer:
                raise PumbaException("It's not your turn!")
            # Intenta hacer el efecto
            game.player_action_switch(Suit[suit])
            cache.set("match_" + self.match_id, game, None)
            # Le da el OK
            self.send_ok()
            # Actualiza el estado de todos
            self.send_game_state_global({"type": "switch", "player": username, "suit": Suit[suit].name})
        except PumbaException as e:
            self.send_error_msg(e)
        except Exception as e:
            self.send_error_msg_generic(e)
                
    # Imprime en pantalla la stack trace y devuelve un mensaje de error al cliente actual
    def send_error_msg(self, exception):
        traceback.print_tb(exception.__traceback__)
        self.send(text_data=json.dumps({
            'type': 'error',
            'message': str(exception),
        }))

    def send_error_msg_generic(self, exception):
        traceback.print_tb(exception.__traceback__)
        print(exception)
        self.send(text_data=json.dumps({
            'type': 'error',
            'message': "An unexpected server error ocurred",
        }))

    # Le envía un mensaje de OK al cliente actual
    def send_ok(self):
        self.send(text_data=json.dumps({
            'type': 'ok'
        }))

    # Envía el estado de juego al cliente actual
    def send_game_state(self, event = None, curgame = None, action = None):
        # Recupera el estado de juego
        if curgame is None:
            game = cache.get(self.match_group_name)
        else:
            game = curgame
        #print("Current: " + str(game.currentPlayer))
        #print("Next: " + str(game.nextPlayer))
        #print("Draw: " + str(len(game.drawPile)))
        #print("Play: " + str(len(game.playPile)))
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

        # Se intenta obtener del evento que ha ejecutado esta función o como parámetro la
        # acción que ha llevado a este nuevo estado de juego
        # Si no hay evento ni acción por parámetro:
        if action and event is None:
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
        elif action is not None:
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
                'players': players,
                'action': action
            }))
        elif event is not None:
            if event.get('action', None) is not None:
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
                'players': players,
                'action': event.get('action')
            }))

    
    # Envía el nuevo estado de juego a todos los jugadores conectados
    def send_game_state_global(self, action = None):
        # Action es la acción que ha llevado a este nuevo estado de juego (robar carta,
        # terminar turno, etc) codificada en JSON
        if action is None:
            async_to_sync(self.channel_layer.group_send)(
                self.match_group_name,
                {
                    'type': 'send_game_state'
                }
            )
        else:
            async_to_sync(self.channel_layer.group_send)(
                self.match_group_name,
                {
                    'type': 'send_game_state',
                    'action': action
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
            'type': 'notification',
            'message': message
        }))