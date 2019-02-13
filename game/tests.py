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


    def test_regular_endturn_drawtwice(self):
        # Intenta robar dos cartas y terminar turno
        self.game.player_action_draw()
        self.game.player_action_draw()
        self.game.begin_turn()
        self.assertEqual(self.game.currentPlayer, 1)