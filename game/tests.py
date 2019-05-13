from django.test import TestCase, LiveServerTestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from channels.testing import ChannelsLiveServerTestCase
from game.domain_objects import *
from django.core.cache import cache 
from django.contrib.auth.models import User
from game import matchmaking
import time
from selenium import webdriver
from game.models import GameKey
from django.urls import reverse
from django.test import Client
from game.forms import MatchForm

# Create your tests here.

# Para llevar el coverage al 100%, aunque no hacen mucho
class DomainModelTestCase(TestCase):
    def setUp(self):
        pass
    
    def test_player_controller(self):
        PlayerController(None, None, None)
        PlayerController(True, None, None)
        PlayerController(False, None, None)

    def test_card_suit_none(self):
        try:
            card = Card(None, CardNumber.ONE)
        except PumbaException as e:
            if(str(e) != "Suit cannot be none"):
                raise

    def test_card_number_none(self):
        try:
            card = Card(Suit.BASTOS, None)
        except PumbaException as e:
            if(str(e) != "Number cannot be none"):
                raise

    def test_action_none(self):
        try:
            action = Action(None)
        except PumbaException as e:
            if(str(e) != "Type cannot be none"):
                raise

    def test_gain_card_none(self):
        try:
            player = Player()
            player.gain_card(None)
        except PumbaException as e:
            if(str(e) != "Card received is None"):
                raise

DECK_SIZE = 8 * 4
class GameTestCase(TestCase):
    def setUp(self):
        self.game = Game()
        for i in range(4):
            self.game.players.append(Player(self.game))
        self.game.host = self.game.players[0]
        self.game.begin_match()

    def test_abnormal_begin_match_already_started(self):
        try:
            self.game.begin_match()
        except PumbaException as e:
            if(str(e) != "The game is already started!"):
                raise

    def test_abnormal_begin_match_no_host(self):
        try:
            game = Game()
            for i in range(4):
                game.players.append(Player(game))
            game.begin_match()
        except PumbaException as e:
            if(str(e) != "There is no defined host for the game"):
                raise

    def test_abnormal_begin_match_no_players(self):
        try:
            game = Game()
            game.host = Player(game)
            game.begin_match()
        except PumbaException as e:
            if(str(e) != "Not enough players! 0"):
                raise

    def test_begin_match_custom_cards(self):
        game = Game()
        for i in range(4):
            game.players.append(Player(game))
        game.host = game.players[0]
        cards = []
        for i in range (100):
            cards.append(Card(Suit.BASTOS, CardNumber.ONE))
        game.begin_match(cards)
        
    def test_regular_draw(self):
        # Roba una carta de manera normal
        self.game.player_action_draw()
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 5)
    
    def test_regular_draw_twice(self):
        # Roba dos cartas de manera normal
        self.game.player_action_draw()
        self.game.player_action_draw()
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 6)

    def test_regular_draw_empty(self):
        # Intenta robar carta cuando la pila de robo está vacía
        self.game.drawPile = []
        self.game.playPile = [Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.players[self.game.currentPlayer].hand = []
        self.game.player_action_draw()
        self.assertEqual(self.game.players[self.game.currentPlayer].hand[0].suit, Suit.ESPADAS)
        self.assertEqual(self.game.players[self.game.currentPlayer].hand[0].number, CardNumber.ONE)

    def test_abnormal_draw_thrice(self):
        # Roba tres cartas, lo que no es legal
        try:
            self.game.player_action_draw()
            self.game.player_action_draw()
            self.game.player_action_draw()
        except IllegalMoveException as e:
            if(str(e) != "Can only draw up to twice per turn!"):
                raise

    def test_abnormal_draw_not_started(self):
        # Roba tres cartas, lo que no es legal
        try:
            game = Game()
            game.player_action_draw()
        except PumbaException as e:
            if(str(e) != "The game is not started!"):
                raise

    def test_abnormal_draw_counternotzero(self):
        # Intenta robar carta cuando el contador de robo no es cero
        try:
            self.game.drawCounter = 1
            self.game.player_action_draw()
        except IllegalMoveException as e:
            if(str(e) != "Draw counter must be zero!"):
                raise

    def test_abnormal_draw_played(self):
        # Intenta robar carta cuando ya se ha hecho otra cosa este turno
        try:
            self.game.turn.add_action(ActionType.PLAY)
            self.game.player_action_draw()
        except IllegalMoveException as e:
            if(str(e) != "Cannot draw if something else has been done this turn!"):
                raise

    def test_abnormal_draw_empty(self):
        # Intenta robar carta cuando no hay cartas en juego
        try:
            self.game.playPile = []
            self.game.drawPile = []
            self.game.player_action_draw()
        except IllegalMoveException as e:
            if(str(e) != "Cannot draw if there are no cards in play!"):
                raise
    
    def test_regular_draw_forced_1(self):
        # Intenta robar una carta de forma forzada
        self.game.drawCounter = 1
        self.game.player_action_draw_forced()
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 5)

    def test_regular_draw_forced_2(self):
        # Intenta robar dos cartas de forma forzada
        self.game.drawCounter = 2
        self.game.player_action_draw_forced()
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 6)

    def test_regular_draw_forced_2_shuffle(self):
        # Intenta robar dos cartas de forma forzada barajando la baraja
        self.game.drawCounter = 2
        pile = self.game.drawPile
        self.game.drawPile = []
        self.game.playPile.extend(pile)
        self.game.player_action_draw_forced()
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 6)

    def test_regular_draw_forced_1_shuffle(self):
        # Intenta robar una carta de forma forzada barajando la baraja
        self.game.drawCounter = 1
        pile = self.game.drawPile
        self.game.drawPile = []
        self.game.playPile.extend(pile)
        self.game.player_action_draw_forced()
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 5)

    def test_regular_draw_forced_100_shuffle(self):
        # Intenta robar 100, agotando por tanto la baraja
        self.game.drawCounter = 100
        self.game.player_action_draw_forced()
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), DECK_SIZE - 3*4)

    def test_abnormal_draw_forced_not_started(self):
        try:
            game = Game()
            game.player_action_draw_forced()
        except PumbaException as e:
            if(str(e) != "The game is not started!"):
                raise

    def test_abnormal_draw_forced_empty(self):
        # Intenta robar forzadamemente cuando el contador es cero
        try:
            self.game.drawCounter = 0
            self.game.player_action_draw_forced()
        except IllegalMoveException as e:
            if(str(e) != "Cannot draw if the counter is zero already!"):
                raise

    def test_abnormal_draw_forced_notbeginning(self):
        # Intenta robar forzadamemente cuando se ha hecho otra cosa
        try:
            self.game.drawCounter = 1
            self.game.turn.add_action(ActionType.DRAW)
            self.game.player_action_draw_forced()
        except IllegalMoveException as e:
            if(str(e) != "Draw from draw counter must be done at the beginning of turn!"):
                raise

    def test_regular_play_one(self):
        # Intenta jugar un ONE
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.ONE), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        self.assertEquals(self.game.drawCounter, 1)
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE - 2)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 1)

    def test_regular_play_two(self):
        # Intenta jugar un TWO
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.TWO), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        self.assertEquals(self.game.drawCounter, 2)
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE - 2)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 1)

    # TODO Todas las posibilidades de COPY
    def test_regular_play_copy_none(self):
        # Intenta copiar un NONE
        self.game.lastEffect = CardNumber.NONE
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.COPY), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE - 2)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 1)

    def test_regular_play_copy_one(self):
        # Intenta copiar un ONE
        self.game.lastEffect = CardNumber.ONE
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.COPY), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        self.assertEquals(self.game.drawCounter, 1)
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE - 2)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 1)

    def test_regular_play_copy_two(self):
        # Intenta copiar un TWO
        self.game.lastEffect = CardNumber.TWO
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.COPY), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        self.assertEquals(self.game.drawCounter, 2)
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE - 2)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 1)

    def test_regular_play_copy_divine(self):
        # Intenta copiar un DIVINE
        self.game.lastEffect = CardNumber.DIVINE
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.COPY), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE - 2)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 1)

    def test_regular_play_copy_switch(self):
        # Intenta copiar un DIVINE
        self.game.lastEffect = CardNumber.SWITCH
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.COPY), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE - 2)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 1)

    def test_regular_play_copy_flip_clockwise(self):
        # Intenta copiar un FLIP
        self.game.lastEffect = CardNumber.FLIP
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.COPY), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE - 2)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 1)
        self.assertEquals(self.game.nextPlayer, 3)
        self.assertEquals(self.game.turnDirection, TurnDirection.COUNTERCLOCKWISE)

    def test_regular_play_copy_flip_counterclockwise(self):
        # Intenta copiar un FLIP
        self.game.lastEffect = CardNumber.FLIP
        self.game.turnDirection = TurnDirection.COUNTERCLOCKWISE
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.COPY), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE - 2)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 1)
        self.assertEquals(self.game.nextPlayer, 1)
        self.assertEquals(self.game.turnDirection, TurnDirection.CLOCKWISE)

    def test_regular_play_copy_jump_clockwise(self):
        # Intenta copiar un JUMP
        self.game.lastEffect = CardNumber.JUMP
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.COPY), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE - 2)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 1)
        self.assertEquals(self.game.nextPlayer, 2)

    def test_regular_play_copy_jump_counterclockwise(self):
        # Intenta copiar un JUMP
        self.game.lastEffect = CardNumber.JUMP
        self.game.turnDirection = TurnDirection.COUNTERCLOCKWISE
        self.game.update_next_player(self.game.currentPlayer)
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.COPY), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE - 2)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 1)
        self.assertEquals(self.game.nextPlayer, 2)

    def test_regular_play_copy_king(self):
        # Intenta copiar un KING
        self.game.lastEffect = CardNumber.KING
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.COPY), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE - 2)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 1)

    def test_regular_play_divine(self):
        # Intenta jugar un DIVINE
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.DIVINE), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE - 2)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 1)

    def test_regular_play_switch(self):
        # Intenta jugar un SWITCH
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.SWITCH), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE - 2)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 1)

    def test_regular_play_flip_clockwise(self):
        # Intenta jugar un FLIP
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.FLIP), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE - 2)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 1)
        self.assertEquals(self.game.nextPlayer, 3)
        self.assertEquals(self.game.turnDirection, TurnDirection.COUNTERCLOCKWISE)

    def test_regular_play_flip_counterclockwise(self):
        # Intenta jugar un FLIP
        self.game.turnDirection = TurnDirection.COUNTERCLOCKWISE
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.FLIP), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE - 2)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 1)
        self.assertEquals(self.game.nextPlayer, 1)
        self.assertEquals(self.game.turnDirection, TurnDirection.CLOCKWISE)

    def test_regular_play_jump_clockwise(self):
        # Intenta jugar un JUMP
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.JUMP), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE - 2)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 1)
        self.assertEquals(self.game.nextPlayer, 2)

    def test_regular_play_jump_counterclockwise(self):
        # Intenta jugar un JUMP
        self.game.turnDirection = TurnDirection.COUNTERCLOCKWISE
        self.game.update_next_player(self.game.currentPlayer)
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.JUMP), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE - 2)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 1)
        self.assertEquals(self.game.nextPlayer, 2)

    def test_regular_play_king(self):
        # Intenta jugar un KING
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.KING), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        count = 0
        for p in self.game.players:
            count = count + len(p.hand)
        count = count + len(self.game.playPile) + len(self.game.drawPile)
        self.assertEquals(count, DECK_SIZE - 2)
        self.assertEquals(len(self.game.players[self.game.currentPlayer].hand), 1)

    def test_regular_play_two_deflect(self):
        # Intenta reflejar con un TWO
        self.game.drawCounter = 1
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.TWO), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)

    def test_regular_play_one_deflect(self):
        # Intenta reflejar con un ONE
        self.game.drawCounter = 1
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.ONE), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)


    def test_abnormal_play_not_started(self):
        try:
            game = Game()
            game.player_action_play(0)
        except PumbaException as e:
            if(str(e) != "The game is not started!"):
                raise

    def test_abnormal_play_invalid_index(self):
        try:      
            self.game.player_action_play(-1)
        except PumbaException as e:
            if(str(e) != "Invalid card index!"):
                raise

    def test_abnormal_play_drawcounter(self):
        # Intenta jugar una carta con el contador de robo activo
        try:
            self.game.drawCounter = 1
            self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.DIVINE), Card(Suit.ESPADAS, CardNumber.ONE)]
            self.game.player_action_play(0)
        except IllegalMoveException as e:
            if(str(e) != "Must deflect card draw with One or Two!"):
                raise

    def test_abnormal_play_twice(self):
        # Intenta jugar dos cartas
        try:
            self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.DIVINE), Card(self.game.lastSuit, CardNumber.DIVINE), Card(Suit.ESPADAS, CardNumber.ONE)]
            self.game.player_action_play(0)
            self.game.player_action_play(0)
        except IllegalMoveException as e:
            if(str(e) != "You already played a card this turn!"):
                raise

    def test_regular_play_playking(self):
        # Intenta jugar una carta después de jugar un KING
        self.game.turn.add_action(ActionType.PLAYKING)
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.ONE), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        self.assertEqual(self.game.lastEffect, CardNumber.NONE)

    def test_abnormal_play_playking_wrongsuit(self):
        # Intenta jugar una carta de un palo erróneo después de jugar un KING
        try:
            self.game.turn.add_action(ActionType.PLAYKING)
            self.game.lastSuit = Suit.ESPADAS
            self.game.players[self.game.currentPlayer].hand = [Card(Suit.BASTOS, CardNumber.DIVINE), Card(Suit.ESPADAS, CardNumber.ONE)]
            self.game.player_action_play(0)
        except IllegalMoveException as e:
            if(str(e) != "This card is not of a suitable suit!"):
                raise

    def test_abnormal_play_wrongsuit(self):
        # Intenta jugar una carta de un palo y número erróneo
        try:
            self.game.lastSuit = Suit.BASTOS
            self.game.lastNumber = CardNumber.ONE
            self.game.players[self.game.currentPlayer].hand = [Card(Suit.ESPADAS, CardNumber.DIVINE), Card(Suit.ESPADAS, CardNumber.ONE)]
            self.game.player_action_play(0)
        except IllegalMoveException as e:
            if(str(e) != "That card does not share a suit or number with the last card played!"):
                raise

    def test_nextplayer_clockwise(self):
        self.game.turnDirection = TurnDirection.CLOCKWISE
        self.game.update_next_player(2)
        self.assertEquals(self.game.nextPlayer, 3)

    def test_nextplayer_clockwise_limit(self):
        self.game.turnDirection = TurnDirection.CLOCKWISE
        self.game.update_next_player(3)
        self.assertEquals(self.game.nextPlayer, 0)

    def test_nextplayer_counterclockwise(self):
        self.game.turnDirection = TurnDirection.COUNTERCLOCKWISE
        self.game.update_next_player(2)
        self.assertEquals(self.game.nextPlayer, 1)

    def test_nextplayer_counterclockwise_limit(self):
        self.game.turnDirection = TurnDirection.COUNTERCLOCKWISE
        self.game.update_next_player(0)
        self.assertEquals(self.game.nextPlayer, 3)

    def test_regular_endturn_drawtwice(self):
        # Intenta robar dos cartas y terminar turno
        self.game.player_action_draw()
        self.game.player_action_draw()
        self.game.begin_turn()
        self.assertEqual(self.game.currentPlayer, 1)

    def test_regular_endturn_playcard(self):
        # Juega una carta y termina el turno
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.TWO), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        self.game.begin_turn()

    def test_regular_endturn_playking(self):
        # Juega un KING y termina el turno
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.KING), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        self.game.begin_turn()

    def test_regular_endturn_forceddraw(self):
        # Roba forzadamente y termina turno
        self.game.drawCounter = 2
        self.game.player_action_draw_forced()
        self.game.begin_turn()

    def test_regular_endturn_nocards(self):
        # Termina turno sin hacer nada por no haber cartas en juego
        self.game.playPile = []
        self.game.drawPile = []
        self.game.begin_turn()

    def test_abnormal_endturn_not_started(self):
        try:
            game = Game()
            game.begin_turn()
        except PumbaException as e:
            if(str(e) != "The game is not started!"):
                raise

    def test_abnormal_endturn_none(self):
        # Intenta terminar turno sin hacer nada
        try:
            self.game.begin_turn()
        except IllegalMoveException as e:
            if(str(e) != "Cannot end turn without playing or drawing cards!"):
                raise

    def test_abnormal_endturn_onedraw(self):
        # Intenta terminar turno robando una sola carta
        try:
            self.game.begin_turn()
            self.game.player_action_draw()
        except IllegalMoveException as e:
            if(str(e) != "Cannot end turn without playing or drawing cards!"):
                raise

    def test_regular_switch(self):
        # Cambia el palo
        self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.SWITCH), Card(Suit.ESPADAS, CardNumber.ONE)]
        self.game.player_action_play(0)
        self.game.player_action_switch(Suit.ESPADAS)

    def test_abnormal_switch_error(self):
        # Cambia el palo a uno que no existe
        try:
            self.game.players[self.game.currentPlayer].hand = [Card(self.game.lastSuit, CardNumber.SWITCH), Card(Suit.ESPADAS, CardNumber.ONE)]
            self.game.player_action_play(0)
            self.game.player_action_switch(89)
        except ValueError as e:
            pass
    
    def test_abnormal_switch_noplay(self):
        # Cambia el palo sin haber jugado un switch
        try:
            self.game.player_action_switch(Suit.ESPADAS)
        except IllegalMoveException as e:
            if(str(e) != "Cannot switch!"):
                raise

    def test_abnormal_switch_not_started(self):
        try:
            game = Game()
            game.player_action_switch(Suit.ESPADAS)
        except PumbaException as e:
            if(str(e) != "The game is not started!"):
                raise

class MatchmakingTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user("testuser1", "testuser1@gmail.com", "testuser1")
        self.user2 = User.objects.create_user("testuser2", "testuser2@gmail.com", "testuser2")
        self.user3 = User.objects.create_user("testuser3", "testuser3@gmail.com", "testuser3")
        self.user4 = User.objects.create_user("testuser4", "testuser4@gmail.com", "testuser4")

    def test_regular_create(self):
        # Intenta crear una partida normalmente
        id = matchmaking.create(4, self.user1, "Test game")
        game = cache.get("match_"+id)
        self.assertIsNotNone(cache.get("match_"+id))
        self.assertEquals(self.user1, game.host)

    def test_regular_create_ais(self):
        # Intenta crear una partida normalmente
        id = matchmaking.create(4, self.user1, "Test game", 1)
        game = cache.get("match_"+id)
        self.assertIsNotNone(cache.get("match_"+id))
        self.assertEquals(self.user1, game.host)

    def test_abnormal_create_users(self):
        # Intenta crear una partida con demasiados pocos usuarios
        try:
            id = matchmaking.create(1, self.user1, "Test game")
        except ValueError as e:
            self.assertEquals(str(e), "The number of users must be at least two!")

    def test_abnormal_create_title(self):
        # Intenta crear una partida con demasiados pocos usuarios
        try:
            id = matchmaking.create(2, self.user1, "    ")
        except ValueError as e:
            self.assertEquals(str(e), "The title cannot be empty!")

    def test_abnormal_create_users_many(self):
        # Intenta crear una partida con demasiados usuarios
        try:
            id = matchmaking.create(10, self.user1, "Test game")
        except ValueError as e:
            self.assertEquals(str(e), "The number of users cannot be more than six!")

    def test_abnormal_create_users_many_ais(self):
        # Intenta crear una partida con demasiados usuarios
        try:
            id = matchmaking.create(5, self.user1, "Test game", 6)
        except ValueError as e:
            self.assertEquals(str(e), "Too many AIs! Are you trying to start a revolution?")

    def test_regular_join(self):
        # Se une a una partida normalmente
        id = matchmaking.create(4, self.user1, "Test game")
        matchmaking.join(self.user2, id)

    def test_regular_join_already(self):
        # Se une a una partida normalmente habiendo estado antes
        id = matchmaking.create(4, self.user1, "Test game")
        matchmaking.join(self.user2, id)
        matchmaking.join(self.user2, id)

    def test_abnormal_join_inexistent(self):
        # Intenta unirse a una partida que no existe
        try:
            matchmaking.join(self.user2, "test")
        except PumbaException as e:
            self.assertEquals(str(e), "The match doesn't exist!")

    def test_abnormal_join_full(self):
        # Intenta unirse a una partida llena
        try:
            id = matchmaking.create(2, self.user1, "Test game")
            matchmaking.join(self.user2, id)
            matchmaking.join(self.user3, id)
        except PumbaException as e:
            self.assertEquals(str(e), "The game is full!")

    def test_abnormal_join_started(self):
        # Intenta unirse a una partida que ya haya empezado
        try:
            id = matchmaking.create(2, self.user1, "Test game")
            game = cache.get("match_" + id)
            game.status = GameStatus.PLAYING
            cache.set("match_" + id, game, None)
            matchmaking.join(self.user2, id)
        except PumbaException as e:
            self.assertEquals(str(e), "The game is already started!")

class ViewTestCase(TestCase):
    def setUp(self):
        user1 = User.objects.create_user("john1", "john1@gmail.com", "john1")
        user2 = User.objects.create_user("john2", "john2@gmail.com", "john2")

    def test_index(self):
        # Comprueba que una petición GET al índice devuelve un 200
        c = Client()
        response = c.get("")
        self.assertTrue(response.status_code == 200)

    def test_matchmaking(self):
        c = Client()
        c.login(username='john1', password='john1')
        response = c.get(reverse("matchmaking"))
        self.assertTrue(response.status_code == 200 or response.status_code == 302)

    def test_create_game(self):
        # Comprueba que redirige si se está ya autenticado
        c1 = Client()
        c2 = Client()
        c1.login(username='john1', password='john1')
        c2.login(username='john2', password='john2')
        response = c1.post(reverse("create_match"), {"max_players": 2, "ai_players": 0, "title": "test"})
        self.assertTrue(response.status_code == 200)

        id = response.context["id"]
        response2 = c2.get(reverse("join_match"), {"id": id})
        
    def test_feedback(self):
        c1 = Client()
        c1.login(username='john1', password='john1')
        response1 = c1.get(reverse("feedback"))
        self.assertTrue(response1.status_code == 200)

        response2 = c1.post(reverse("feedback"), {
            "email": "test@gmail.com",
            "subject": "test9999999999",
            "body": "body9999999999999"
        })
        self.assertTrue(response2.status_code == 200 or response2.status_code == 302)

        response3 = c1.post(reverse("feedback"), {
            "email": "notanemail",
            "subject": "",
            "body": ""
        })
        self.assertTrue(response3.status_code == 200)