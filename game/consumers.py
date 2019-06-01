from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
import json
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist 
from game.exceptions import PumbaException
import traceback
from game.domain_objects import GameStatus, CardNumber, Suit, TurnDirection, ActionType
from game.models import GameKey

class GameConsumer(WebsocketConsumer):
    def connect(self):
        # Si ocurre algo, rechazamos la conexión
        error = False
        # Este atributo sirve luego para saber si este websocket queda cerrado por abrir otro por el mismo usuario en la misma partida
        self.disconnected_by_substitute = False
        # Este atributo sirve luego para saber si se ha desconectado porque la partida ha estado inactiva demasiado tiempo
        self.game_timed_out = False

        # Cogemos el usuario autenticado
        user = None
        try:
            user = self.scope["user"]
            if user is None:
                error = True
        except:
            error = True

        # Guardamos la ID del usuario
        self.user_id = user.id

        # Intentamos obtener la partida de la caché
        self.match_id = self.scope['url_route']['kwargs']['match_id']
        self.match_group_name = 'match_%s' % self.match_id
        game = None
        try:
            game = self.retrieve_from_cache()
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

        # Si ya está conectado en otra pestaña no le dejamos tener dos consumidores abiertos
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

        # Si todo ha ido bien, nos conectamos normalmente
        if not error:
            # Anotamos que el jugador está online
            game.players[self.player_index].controller.isAI = False
            # Actualizamos la caché
            self.save_to_cache(game)
            # Se une al grupo de canales de la partida
            async_to_sync(self.channel_layer.group_add)(
                self.match_group_name,
                self.channel_name
            )
            # Comprobamos si la key en la BD está creada; si no, la creamos
            try:
                GameKey.objects.get(key = self.match_id)
            except ObjectDoesNotExist:
                # Nos aseguramos de que el que la ha creado es el host
                if game.host.id is not user.id:
                    raise ValueError("The host is not the same as the logged user!")
                key = GameKey(status = game.status.name, key = self.match_id, current_users = 1, max_users = game.maxPlayerCount, name=game.title, ai_count = game.aiCount, capacity = game.maxPlayerCount - game.aiCount)
                key.save()
                key.users.add(user)
                key.save()
            # Enviamos notificación por chat de que un usuario se ha unido
            notificationmsg = "User " + game.players[self.player_index].name + " joined the game"
            self.send_notification_global(notificationmsg)
            self.was_connected_successfully_to_game = True
            # Finalmente, aceptamos la conexión
            self.accept()
            # TODO Comprobar si hay consumidores que no respondan pero sus jugadores aparezcan
            # conectados y desconectarlos.
        else:
            # Si ha pasado algo, rechazamos la conexión
            self.was_connected_successfully_to_game = False
            self.send(text_data=json.dumps({
                'type': 'disconnect',
                'reason': 'Could not connect to the match'
            }))
            #self.close()

    # Se ejecuta cuando otro websocket del mismo jugador se conecta y le envía un evento para decirle que este se desconecte (en connect(self))
    def substitute_disconnect(self, event):
        # Connect envía el mensaje de desconectarse a todo el canal, así que comprobamos primero si va a nosotros
        user_id = event['user_id']
        if user_id is self.user_id:
            # Cuando se conecta el usuario abriendo un websocket nuevo, cerramos el viejo
            # Se avisa al cliente
            self.send(text_data=json.dumps({
                'type': 'disconnect',
                'reason': "You opened the game on another window; closing this one"
            }))
            # Actualizamos a todos los jugadores por si acaso
            self.send_game_state_global()
            # Dejamos el canal
            self.disconnected_by_substitute = True
            self.close()


    def disconnect(self, close_code):
        if self.was_connected_successfully_to_game and not self.disconnected_by_substitute:
            # Cogemos la partida
            game = self.retrieve_from_cache()
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
                self.save_to_cache(game, 1)
                try:
                    GameKey.objects.get(key = self.match_id).delete()
                except:
                    pass
            else:
                # Si el host se desconecta, ponemos a otro de host
                if game.host is game.players[self.player_index].controller.user:
                    for player in game.players:
                        if not player.controller.isAI:
                            game.host = player.controller.user
                            self.send_notification_global(player.name + " is the new host")
                            break
                self.save_to_cache(game)
                # Actualizamos a todos los jugadores
                self.send_game_state_global()
                # Antes de irse, hace jugar a la IA si es necesario
                self.do_ai(game)

        # Dejamos el canal
        async_to_sync(self.channel_layer.group_discard)(
            self.match_group_name,
            self.channel_name
        )

    # Recibe mensajes del websocket
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        pkgtype = text_data_json['type']

        game = self.retrieve_from_cache()
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

        # Lo cortamos a 100 caracteres
        if len(text) > 100:
            text = text[0:100]
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
            game = self.retrieve_from_cache()
            # Comprueba que es el host
            user = self.scope["user"]
            if game.host.id is not user.id:
                raise PumbaException("You are not the host!")
            else:
                # Actualiza el estado en la BD
                key = GameKey.objects.get(key = self.match_id)
                key.status = "PLAYING"
                key.save()
                # Hace el procesamiento de empezar la partida
                game.begin_match()
                self.save_to_cache(game)
                # Le da el OK
                self.send_ok()
                # Actualiza el estado de todos
                self.send_game_state_global({"type": "begin_match"})
                # Si el primer jugador es una IA:
                self.do_ai(game)
        except PumbaException as e:
            self.send_error_msg(e)
        except Exception as e:
            self.send_error_msg_generic(e)

    def trigger_begin_turn(self):
        try:
            # Recupera la partida
            game = self.retrieve_from_cache()
            username = game.players[self.player_index].name
            # Comprueba que es su turno
            if self.player_index is not game.currentPlayer:
                raise PumbaException("It's not your turn!")
            # Intenta terminar el turno
            game.begin_turn()
            self.save_to_cache(game)
            # Le da el OK
            self.send_ok()
            # Actualiza el estado de todos
            self.send_game_state_global({"type": "end_turn", "player": username})
            # Si el siguiente jugador es una IA, que haga cosas de IA
            # TODO No se envían los game states bien cuando los envía la IA
            # O bien que el send_game_state_global envíe opcionalmente el game actual o bien
            # decirle al frontend que ignore los estados de la IA (apaño mierder)
            # TODO Si la IA no puede robar cartas porque no hay cartas en la pila se queda pillada
            self.do_ai(game)
        except PumbaException as e:
            self.send_error_msg(e)
        except Exception as e:
            self.send_error_msg_generic(e)

    # Inicia un loop que hace jugar a la IA hasta el siguiente jugador humano
    # Llamar cada vez que sea posible que el jugador actual sea una IA
    def do_ai(self, game):
        if game.status is GameStatus.PLAYING:
            try:
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
                                self.save_to_cache(game)
                                self.send_game_state_global({"type": "end_turn", "player": ai_player.name, "ai": True})
                                needs_draw = False
                                break
                        if (needs_draw):
                            forced_draw = game.drawCounter
                            game.player_action_draw_forced()
                            self.send_game_state_global({"type": "draw_card_forced", "player": ai_player.name, "number": forced_draw})
                            game.begin_turn()
                            self.save_to_cache(game)
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
                                # Si se queda sin cartas gana
                                if len(game.players[game.currentPlayer].hand) == 0:
                                    self.send_game_state_global(self.send_game_state_global({"type": "game_won", "player": ai_player.name}))
                                    game.status = GameStatus.ENDING
                                    #game.points[self.player_index] = game.points[self.player_index] + 1
                                    self.save_to_cache(game)
                                    # Actualiza el estado en la BD
                                    key = GameKey.objects.get(key = self.match_id)
                                    key.status = "ENDING"
                                    key.save()
                                    break
                                else:
                                    game.begin_turn()
                                    self.save_to_cache(game)
                                    self.send_game_state_global({"type": "end_turn", "player": ai_player.name})
                                    break
                        # Si no puede jugar ninguna, roba dos cartas y termina su turno
                        if cannot_play:
                            # Si la pila de cartas está vacía, termina el turno directamente
                            if len(game.drawPile) is 0 and len(game.playPile) is 0:
                                game.begin_turn()
                                self.save_to_cache(game)
                                self.send_game_state_global({"type": "end_turn", "player": ai_player.name})
                            else:
                                game.player_action_draw()
                                self.send_game_state_global({"type": "draw_card", "player": ai_player.name})
                                if not (len(game.drawPile) is 0 and len(game.playPile) is 0):
                                    game.player_action_draw()
                                    self.send_game_state_global({"type": "draw_card", "player": ai_player.name})
                                game.begin_turn()
                                self.save_to_cache(game)
                                self.send_game_state_global({"type": "end_turn", "player": ai_player.name})
                    self.save_to_cache(game)
                    self.send_game_state_global()
            except Exception as e:
                print("Error con la IA: " + str(e))
                traceback.print_tb(e.__traceback__)
                try:
                    #game.begin_turn()
                    game.currentPlayer = game.nextPlayer
                    game.update_next_player(game.currentPlayer)
                    self.save_to_cache(game)
                    self.send_game_state_global({"type": "end_turn", "player": ai_player.name})
                except Exception as e:
                    print("Fallback de IA ha fallado: " + str(e))
                    traceback.print_tb(e.__traceback__)
            

    def trigger_draw_card(self):
        try:
            # Recupera la partida
            game = self.retrieve_from_cache()
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
            self.save_to_cache(game)
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
            game = self.retrieve_from_cache()
            username = game.players[self.player_index].name
            # Comprueba que es su turno
            if self.player_index is not game.currentPlayer:
                raise PumbaException("It's not your turn!")
            # Recupera la carta que quiere jugar
            index = int(index)
            card = game.players[self.player_index].hand[index]
            # Intenta jugar la carta
            game.player_action_play(index)
            self.save_to_cache(game)
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
                game.points[self.player_index] = game.points[self.player_index] + 1
                self.save_to_cache(game)
                # Actualiza el estado en la BD
                key = GameKey.objects.get(key = self.match_id)
                key.status = "ENDING"
                key.save()
        except PumbaException as e:
            self.send_error_msg(e)
        except Exception as e:
            self.send_error_msg_generic(e)
    
    def trigger_switch_effect(self, suit):
        try:
            # Recupera la partida
            game = self.retrieve_from_cache()
            username = game.players[self.player_index].name
            # Comprueba que es su turno
            if self.player_index is not game.currentPlayer:
                raise PumbaException("It's not your turn!")
            # Intenta hacer el efecto
            game.player_action_switch(Suit[suit])
            self.save_to_cache(game)
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
            game = self.retrieve_from_cache()
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
            #players.append([player.name, len(player.hand), player.controller.isAI, 0])
            players.append([player.name, len(player.hand), player.controller.isAI, game.points[game.players.index(player)]])

        # Quién es el host actual de la partida
        host = None
        for i in range(len(game.players)):
            if game.players[i].controller.user is not None:
                if game.players[i].controller.user.id is game.host.id:
                    host = i
                    break

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
                'players': players,
                'host': host
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
                'host': host,
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
                    'host': host,
                    'action': event.get('action')
                }))
            else:
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
                    'host': host
                }))
        else:
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
                'host': host
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

    def save_to_cache(self, game, timeout = None):
        # Guarda la partida en la caché con un timeout
        if timeout is None:
            cache.set("match_" + self.match_id, game, 600)
        else:
            cache.set("match_" + self.match_id, game, timeout)

    def retrieve_from_cache(self):
        # Recuperamos la instancia de juego
        result = cache.get(self.match_group_name, None)
        # Si es None, el juego ha hecho timeout, por lo que nos desconectamos y borramos la partida
        if result is None:
            self.game_timed_out = True
            self.send(text_data=json.dumps({
                'type': 'disconnect',
                'reason': 'Match timed out due to inactivity'
            }))
            try:
                GameKey.objects.get(key = self.match_id).delete()
            except:
                pass
            # Dejamos el canal
            async_to_sync(self.channel_layer.group_discard)(
                self.match_group_name,
                self.channel_name
            )
            self.close()
        else:
            return result
