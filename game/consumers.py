from channels.generic.websocket import WebsocketConsumer, AsyncWebsocketConsumer
from asgiref.sync import async_to_sync
import json
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist 
from django.contrib.auth.models import User
from game.exceptions import PumbaException
import traceback
from game.domain_objects import GameStatus, CardNumber, Suit, TurnDirection, ActionType, Card, AIDifficulty
from game.models import GameKey, getUserProfilePictureUrl
import time
import random
import copy
from pumba.settings import CHEATS_ENABLED
from django.utils.translation import gettext as _

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
            self.send_notification_global(notificationmsg, {"event": "connect", "player": self.player_index})
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
                'reason': _('Could not connect to the match')
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
                'reason': _("You opened the game on another window; closing this one")
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
            notificationmsg = _("User %(username)s disconnected from the game") % {"username": username}
            self.send_notification_global(notificationmsg, {"event": "disconnect", "player": self.player_index})
            
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
                            self.send_notification_global(_("%(player)s is the new host") % {"player": player.name}, {"event": "host_change", "player": self.player_index})
                            break
                self.save_to_cache(game)
                # Actualizamos a todos los jugadores
                self.send_game_state_global()
                # Antes de irse, hace jugar a la IA si es necesario
                self.do_ai()

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
        elif pkgtype == "profile_picture":
            self.send_profile_picture(text_data_json['index'])
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
        elif pkgtype == "debug":
            self.cheat(text_data_json)

    def send_profile_picture(self, index):
        # Recuperamos el estado de juego
        game = self.retrieve_from_cache()
        # Si es un identificador válido, devolvemos la imagen de perfil adecuada
        if index < len(game.players) and index > -1:
            controller = game.players[index].controller
            if controller.user is None:
                picture = picture = "/static/ai-prof-picture.png"
            else:
                picture = getUserProfilePictureUrl(User.objects.get(id = controller.user.id))

            self.send(text_data=json.dumps({
                'type': 'profile_picture',
                'index': index,
                'picture': picture
            }))

    # Te permite hacer trampas para debugear
    def cheat(self, message):
        try:
            # Comprobamos que las trampas están activadas
            if not CHEATS_ENABLED:
                return None
            cheat = message.get('cheat', None)
            game = self.retrieve_from_cache()
            # Añade una carta arbitraria a la mano dado un Suit y un Number
            if cheat == "add_card":
                card = Card(Suit[message['suit']], CardNumber[message['number']])
                game.players[int(message['player'])].hand.append(card)
                self.save_to_cache(game)
            # Elimina la carta i del jugador j
            elif cheat == "remove_card":
                player_index = message["player_index"]
                card_index = message["card_index"]
                game.players[player_index].hand.pop(card_index)
                self.save_to_cache(game)
            # Cambia el palo actual
            elif cheat == "change_suit":
                suit = message['suit']
                suit = Suit[suit]
                game.lastSuit = suit
                self.save_to_cache(game)
            # Cambia el número actual y el último efecto
            elif cheat == "change_number":
                number = message['number']
                number = CardNumber[number]
                game.lastNumber = number
                if number == CardNumber.COPY:
                    game.lastEffect = CardNumber.NONE
                else:
                    game.lastEffect = number
                self.save_to_cache(game)

            # Actualizamos información privilegiada y enviamos el estado a todos
            self.send_privileged_info()
            self.queue_send_game_state_global(game, None)
        except Exception as e:
            print(e)
            traceback.print_tb(e.__traceback__)

    # Envía las manos de TODOS los jugadores. Para hacer trampas.
    def send_privileged_info(self):
        game = self.retrieve_from_cache()

        hands = []
        for i in range(len(game.players)):
            hand = self.get_player_hand(game, i)
            hands.append(hand)

        self.send(text_data=json.dumps({
            'type': 'cheat_info',
            'hands': hands
        }))

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
                raise PumbaException(_("You are not the host!"))
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
                self.queue_send_game_state_global(game, {"type": "begin_match"})
                # Si el primer jugador es una IA:
                self.do_ai()
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
                raise PumbaException(_("It's not your turn!"))
            # Intenta terminar el turno
            game.begin_turn()
            self.save_to_cache(game)
            # Le da el OK
            self.send_ok()
            # Actualiza el estado de todos
            self.queue_send_game_state_global(game, {"type": "end_turn", "player": username})
            # Si el siguiente jugador es una IA, que haga cosas de IA
            self.do_ai()
        except PumbaException as e:
            self.send_error_msg(e)
        except Exception as e:
            self.send_error_msg_generic(e)

    def ai_send_game_state_global(self, game, action):
        #self.send_game_state_global(action = None, game = self.encode_game_state(game, action))
        self.queue_send_game_state_global(game, action)

    def queue_send_game_state_global(self, game, action):
        self.send_game_state_global(action = None, game = self.encode_game_state(game, action))

    # Inicia un loop que hace jugar a la IA hasta el siguiente jugador humano
    # Llamar cada vez que sea posible que el jugador actual sea una IA
    def do_ai(self):
        # Cuando se "envía" un mensaje aquí (send_game_state_global) se pone en cola y se envía cuando se ha terminado de procesar la IA
        # Por eso, hay que pasarle por parámetro el estado concreto que se quiere, o si no todos los mensajes cogen el último estado.
        game = self.retrieve_from_cache()
        if game.status is GameStatus.PLAYING:
                while game.players[game.currentPlayer].controller.isAI:
                    try:
                        if game.aiDifficulty is AIDifficulty.EASY:
                            self.do_easy_ai(game)
                        elif game.aiDifficulty is AIDifficulty.MEDIUM:
                            self.do_medium_ai(game)
                        else:
                            self.do_hard_ai(game)
                    except Exception as e:
                        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>Error con la IA: " + str(e))
                        traceback.print_tb(e.__traceback__)
                        try:
                            #game.begin_turn()
                            ai_player = game.players[game.currentPlayer]
                            game.currentPlayer = game.nextPlayer
                            game.update_next_player(game.currentPlayer)
                            self.save_to_cache(game)
                            self.ai_send_game_state_global(game, {"type": "end_turn", "player": ai_player.name})
                        except Exception as e:
                            print("Fallback de IA ha fallado: " + str(e))
                            traceback.print_tb(e.__traceback__)

    def do_easy_ai(self, game):
        # Si hay contador de robo, o refleja o roba.
        if game.drawCounter > 0:
            self.ai_action_try_deflect(game)
        # Si no hay contador de robo, intenta jugar una carta aleatoria
        else:
            result = self.ai_action_play_random_card(game)
            if result is None:
                self.ai_action_draw_card(game)
                self.ai_action_draw_card(game)
            else:
                pass
        self.ai_action_check_if_won(game)
        # Pase lo que pase, se termina el turno
        self.ai_action_end_turn(game)
        self.save_to_cache(game)
        #self.ai_send_game_state_global(game, None)

    def do_medium_ai(self, game):
        # Si hay contador de robo, o refleja o roba.
        if game.drawCounter > 0:
            res = self.ai_action_try_deflect(game)
            # Si no ha podido reflejar, intenta jugar una carta aleatoria
            if res is None:
                self.ai_action_play_random_card(game)
        # Si no hay contador de robo, intenta jugar una carta aleatoria
        else:
            result = self.ai_action_play_random_card(game)
            # Si no ha podido jugar carta
            if result is None:
                # Roba una carta
                self.ai_action_draw_card(game)
                # Intenta jugar carta de nuevo
                result2 = self.ai_action_play_random_card(game)
                # Si tampoco ha podido jugar la carta nueva, roba una última vez y juega esta nueva carta si es posible
                if result2 is None:
                    self.ai_action_draw_card(game)
                    self.ai_action_play_random_card(game)
        # Si se queda sin cartas gana
        self.ai_action_check_if_won(game)
        # Pase lo que pase, se termina el turno
        self.ai_action_end_turn(game)
        self.save_to_cache(game)
        #self.ai_send_game_state_global(game, None)

    def do_hard_ai(self, game):
        # Si hay contador de robo, o refleja o roba.
        if game.drawCounter > 0:
            res = self.ai_action_try_deflect(game)
            # Si no ha podido reflejar, intenta jugar una carta
            if res is None:
                self.ai_action_play_best_card(game)
        # Si no hay contador de robo, intenta jugar una carta
        else:
            result = self.ai_action_play_best_card(game)
            # Si no ha podido jugar carta
            if result is None:
                # Roba una carta
                self.ai_action_draw_card(game)
                # Intenta jugar carta de nuevo
                result2 = self.ai_action_play_best_card(game)
                # Si tampoco ha podido jugar la carta nueva, roba una última vez y juega esta nueva carta si es posible
                if result2 is None:
                    self.ai_action_draw_card(game)
                    self.ai_action_play_best_card(game)
        # Si se queda sin cartas gana
        self.ai_action_check_if_won(game)
        # Pase lo que pase, se termina el turno
        self.ai_action_end_turn(game)
        self.save_to_cache(game)

    def ai_action_play_best_card(self, game):
        # Busca la mejor carta que jugar
        ai_player = game.players[game.currentPlayer]
        ai_hand = game.players[game.currentPlayer].hand
        result = None
        best = None
        score = None
        print("Evaluating choices of " + str(ai_player.name))
        print("\tHand:")
        for i in range(len(ai_hand)):
            print("\t\t" + self.card_to_string(ai_hand[i]) + " (" + str(i) + ")")
        # Por cada carta jugable en la mano, calculamos su puntuación y escogemos la mayor
        for i in range(len(ai_hand)):
            card = ai_hand[i]
            if card.suit is game.lastSuit or card.number is game.lastNumber:
                print("\tChoice " + str(i))
                current_score = self.ai_calculate_card_score(card, game)
                if score is None or current_score > score:
                    if best is not None:
                        print("\t\tUpdating choices: " + self.card_to_string(ai_hand[best]) + " -> " + self.card_to_string(card) + " (" + str(i) + ")")
                    else:
                        print("\t\tUpdating choices: " + "None" + " -> " + self.card_to_string(card) + " (" + str(i) + ")")
                    best = i
                    score = current_score
        if best is not None:
            card = ai_hand[best]
            result = card
            game.player_action_play(best)
            self.save_to_cache(game)
            self.ai_send_game_state_global(game, {"type": "play_card", "player": ai_player.name, "card": {"suit": Suit(card.suit).name, "number": CardNumber(card.number).name}})
            # Si se ha jugado un rey, jugamos todas las del mismo palo
            if card.number is CardNumber.KING:
                ai_hand = game.players[game.currentPlayer].hand
                pending = []
                for i in range(len(ai_hand)):
                    if ai_hand[i].suit is card.suit:
                        pending.insert(0, i)
                for i in range(len(pending)):
                    pcard = ai_hand[pending[i]]
                    game.player_action_play(pending[i])
                    self.ai_send_game_state_global(game, {"type": "play_card", "player": ai_player.name, "card": {"suit": Suit(pcard.suit).name, "number": CardNumber(pcard.number).name}})
                self.save_to_cache(game)
            # Si se ha jugado un switch, cambiamos al palo que sea
            elif card.number is CardNumber.SWITCH:
                ai_hand = game.players[game.currentPlayer].hand
                scoreboard = self.count_hand_suits(ai_hand)
                maxi = max(scoreboard)
                if maxi is scoreboard[0]:
                    game.player_action_switch(Suit.ESPADAS)
                    self.ai_send_game_state_global(game, {"type": "switch", "player": ai_player.name, "suit": game.lastSuit.name})
                elif maxi is scoreboard[1]:
                    game.player_action_switch(Suit.BASTOS)
                    self.ai_send_game_state_global(game, {"type": "switch", "player": ai_player.name, "suit": game.lastSuit.name})
                elif maxi is scoreboard[2]:
                    game.player_action_switch(Suit.COPAS)
                    self.ai_send_game_state_global(game, {"type": "switch", "player": ai_player.name, "suit": game.lastSuit.name})
                else:
                    game.player_action_switch(Suit.OROS)
                    self.ai_send_game_state_global(game, {"type": "switch", "player": ai_player.name, "suit": game.lastSuit.name})
                self.save_to_cache(game)

        return result

    def ai_calculate_card_score(self, card, game):
        print("\t\tCalculating score of " + str(card.number) + " of " + str(card.suit))
        score = None
        if card.number is CardNumber.ONE or card.number is CardNumber.TWO:
            score = self.ai_calculate_ONE_score(card, game)
        elif card.number is CardNumber.KING:
            score = self.ai_calculate_KING_score(card, game)
        elif card.number is CardNumber.SWITCH:
            score = self.ai_calculate_SWITCH_score(card, game)
        elif card.number is CardNumber.COPY:
            if game.lastEffect is not CardNumber.COPY:
                score = self.ai_calculate_card_score(Card(card.suit, game.lastEffect), game)
            else:
                score = 1
        else:
            score = 1
        print("\t\t\tResult: " + str(score))
        return score

    def ai_calculate_ONE_score(self, card, game):
        # Vale más cuantas más ONE, TWO y COPY se tenga en la mano
        ai_hand = game.players[game.currentPlayer].hand
        score = 0.5
        for i in range(len(ai_hand)):
            if ai_hand[i] is not card:
                if ai_hand[i].number is CardNumber.ONE or ai_hand[i].number is CardNumber.TWO:
                    score += 1
                elif ai_hand[i].number is CardNumber.COPY:
                    score += 0.5
        return score

    def ai_calculate_KING_score(self, card, game):
        # Vale más cuantas más cartas del mismo palo haya
        # Empieza a 0.75 para que priorize KING sobre ONE y cartas cualquiera sobre KING si no tiene más que jugar
        ai_hand = game.players[game.currentPlayer].hand
        score = 0.75
        for i in range(len(ai_hand)):
            if ai_hand[i] is not card:
                if ai_hand[i].suit is card.suit:
                    score += 1
        return score

    def ai_calculate_SWITCH_score(self, card, game):
        # Vale más cuantas más cartas del mismo palo hay
        ai_hand = game.players[game.currentPlayer].hand
        std_score = 0.6
        scoreboard = self.count_hand_suits(ai_hand)
        return max(scoreboard) * std_score

    def count_hand_suits(self, hand):
        espadas = 0
        bastos = 0
        copas = 0
        oros = 0
        for i in range(len(hand)):
            if hand[i].suit is Suit.BASTOS:
                bastos += 1
            elif hand[i].suit is Suit.ESPADAS:
                espadas += 1
            elif hand[i].suit is Suit.OROS:
                oros += 1
            elif hand[i].suit is Suit.COPAS:
                copas += 1
        scoreboard = [espadas, bastos, copas, oros]
        return scoreboard


    def ai_action_play_random_card(self, game):
        result = None
        ai_player = game.players[game.currentPlayer]
        ai_hand = game.players[game.currentPlayer].hand
        # Busca una carta cualquiera que jugar
        for i in range(len(ai_hand)):
            card = ai_hand[i]
            if card.suit is game.lastSuit or card.number is game.lastNumber:
                result = card
                game.player_action_play(i)
                self.save_to_cache(game)
                self.ai_send_game_state_global(game, {"type": "play_card", "player": ai_player.name, "card": {"suit": Suit(card.suit).name, "number": CardNumber(card.number).name}})
                break
        return result

    # Intenta reflejar un contador de robo
    # Devuelve None si no ha podido reflejarlo o una carta si ha podido
    def ai_action_try_deflect(self, game):
        ai_player = game.players[game.currentPlayer]
        ai_hand = game.players[game.currentPlayer].hand
        needs_draw = True
        fcard = None
        for i in range(len(ai_hand)):
            card = ai_hand[i]
            if card.number is CardNumber.ONE or card.number is CardNumber.TWO or (card.number is CardNumber.COPY and card.suit is game.lastSuit):
                game.player_action_play(i)
                self.ai_send_game_state_global(game, {"type": "play_card", "player": ai_player.name, "card": {"suit": Suit(card.suit).name, "number": CardNumber(card.number).name}})
                needs_draw = False
                fcard = card
                break
        if (needs_draw):
            forced_draw = game.drawCounter
            game.player_action_draw_forced()
            self.ai_send_game_state_global(game, {"type": "draw_card_forced", "player": ai_player.name, "number": forced_draw})

        return fcard

    def ai_action_check_if_won(self, game):
        ai_player = game.players[game.currentPlayer]
        if len(game.players[game.currentPlayer].hand) == 0:
            self.ai_send_game_state_global(game, {"type": "game_won", "player": ai_player.name})
            game.status = GameStatus.ENDING
            #game.points[self.player_index] = game.points[self.player_index] + 1
            self.save_to_cache(game)
            # Actualiza el estado en la BD
            key = GameKey.objects.get(key = self.match_id)
            key.status = "ENDING"
            key.save()
            return True
        else:
            return False

    def ai_action_draw_card(self, game):
        ai_player = game.players[game.currentPlayer]
        if len(game.drawPile) is 0 and len(game.playPile) is 0:
            return None
        else:
            card = game.player_action_draw()
            self.save_to_cache(game)
            self.ai_send_game_state_global(game, {"type": "draw_card", "player": ai_player.name})
            return card

    def ai_action_end_turn(self, game):
        if game.status is GameStatus.PLAYING:
            ai_player = game.players[game.currentPlayer]
            game.begin_turn()
            self.save_to_cache(game)
            self.ai_send_game_state_global(game, {"type": "end_turn", "player": ai_player.name})

    def card_to_string(self, card):
        return str(card.number.name) + " of " + str(card.suit.name)


    def trigger_draw_card(self):
        try:
            # Recupera la partida
            game = self.retrieve_from_cache()
            username = game.players[self.player_index].name
            # Comprueba que es su turno
            if self.player_index is not game.currentPlayer:
                raise PumbaException(_("It's not your turn!"))
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
                self.queue_send_game_state_global(game, {"type": "draw_card_forced", "player": username, "number": forced_draw})
            else:
                self.queue_send_game_state_global(game, {"type": "draw_card", "player": username})
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
                raise PumbaException(_("It's not your turn!"))
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
            self.queue_send_game_state_global(game, {"type": "play_card", "player": username, "card": {"suit": Suit(card.suit).name, "number": CardNumber(card.number).name}})
            # Comprueba si se ha ganado la partida
            if len(game.players[self.player_index].hand) == 0:
                self.queue_send_game_state_global(game, {"type": "game_won", "player": username})
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
                raise PumbaException(_("It's not your turn!"))
            # Intenta hacer el efecto
            game.player_action_switch(Suit[suit])
            self.save_to_cache(game)
            # Le da el OK
            self.send_ok()
            # Actualiza el estado de todos
            self.queue_send_game_state_global(game, {"type": "switch", "player": username, "suit": Suit[suit].name})
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
            'message': _("An unexpected server error ocurred"),
        }))

    # Le envía un mensaje de OK al cliente actual
    def send_ok(self):
        self.send(text_data=json.dumps({
            'type': 'ok'
        }))

    # Envía el estado de juego al cliente actual
    def send_game_state(self, event = None):
        if event is not None:
            curgame = copy.deepcopy(event.get('curgame', None))
        else:
            curgame = None
        # Si no se le ha enviado un estado concreto que enviar:
        if curgame is None:
            # Recupera el estado de juego
            game = self.retrieve_from_cache()
            # Se intenta obtener del evento que ha ejecutado esta función o como parámetro la acción que ha llevado a este nuevo estado de juego
            if event is not None and event.get('action', None) is not None and action is None:
                action = event.get('action')
            else:
                action = None
            # Se codifica, se pasa a JSON y se envía
            curgame = self.encode_game_state(game, action)
            curgame['hand'] = curgame.get('hands', None)[self.player_index]
            curgame.pop("hands", None)
            self.send(text_data=json.dumps(curgame))
        # Si se le ha enviado un estado concreto por parámetro:
        else:
            curgame['hand'] = curgame.get('hands', None)[self.player_index]
            curgame.pop("hands", None)
            self.send(text_data=json.dumps(curgame))
 

    def get_player_hand(self, game, index):
        # Recupera las cartas de la mano
        cards = game.players[index].hand
        hand = []
        # Las transforma a un formato más cómodo
        for card in cards:
            hand.append([Suit(card.suit).name, CardNumber(card.number).name])
        return hand

    # Dado un estado de juego (y opcionalmente una acción), devuelve un diccionario con los datos bien codificados listos para enviar por parámetro o convertir a JSON
    # NOTA: No incluye la mano actual, si no las manos de todos los jugadores. Antes de enviarlo, en el consumidor concreto, hay que eliminar esos datos y poner la mano concreta
    # Esta no es la mejor arquitectura para hacerlo, pero básicamente estos arreglos han llegado muy tarde
    def encode_game_state(self, game = None, action = None):
        if game is None:
            game = self.retrieve_from_cache()
        # Recupera las cartas de las manos
        hands = []
        for i in range(len(game.players)):
            hand = self.get_player_hand(game, i)
            hands.append(hand)

        # Lista de jugadores
        # 0: Nickname
        # 1: Cartas en la mano
        # 2: Estado de conexión (Conectado, IA)
        players = []
        for player in game.players:
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

        res = {
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
            'hands': hands,
            'players': players,
            'host': host,
            'action': action,
            'random': random.random()
        }

        return res


    # Envía el nuevo estado de juego a todos los jugadores conectados
    def send_game_state_global(self, action = None, game = None):
        # Action es la acción que ha llevado a este nuevo estado de juego (robar carta, terminar turno, etc) codificada en JSON
        async_to_sync(self.channel_layer.group_send)(
            self.match_group_name,
            {
                'type': 'send_game_state',
                'action': action,
                'curgame': game
            }
        )
    
    # Envía un mensaje de notificación a todos los clientes
    def send_notification_global(self, text, options = None):
        async_to_sync(self.channel_layer.group_send)(
            self.match_group_name,
            {
                'type': 'chat_notification',
                'message': text,
                'info': options
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
        info = event['info']

        # Envía el mensaje al websocket en cliente
        self.send(text_data=json.dumps({
            'type': 'notification',
            'message': message,
            'info': info
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
                'reason': _('Match timed out due to inactivity')
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
