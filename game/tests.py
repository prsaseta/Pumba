from django.test import TestCase
from game.domain_objects import *

# Create your tests here.
DECK_SIZE = 8 * 4
class GameTestCase(TestCase):
    def setUp(self):
        self.game = Game()
        for i in range(4):
            self.game.players.append(Player(self.game))
        self.game.host = self.game.players[0]
        self.game.begin_match()
    
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

    def test_regular_endturn_drawtwice(self):
        # Intenta robar dos cartas y terminar turno
        self.game.player_action_draw()
        self.game.player_action_draw()
        self.game.begin_turn()
        self.assertEqual(self.game.currentPlayer, 1)