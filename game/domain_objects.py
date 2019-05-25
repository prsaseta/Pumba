import enum
import random
import math
from game.exceptions import ConcurrencyError, IllegalMoveException, PumbaException
from copy import deepcopy

# Enumerados
class Suit(enum.Enum):
    ESPADAS = 1
    BASTOS = 2
    COPAS = 3
    OROS = 4

class GameStatus(enum.Enum):
    WAITING = 1
    PLAYING = 2
    ENDING = 3

class CardNumber(enum.Enum):
    ONE = 1
    TWO = 2
    COPY = 3
    DIVINE = 4
    FLIP = 5
    SWITCH = 6
    JUMP = 7
    KING = 8
    NONE = 9

class ActionType(enum.Enum):
    DRAWCOUNTER = 1
    DRAW = 2
    PLAY = 3
    PLAYKING = 4
    SWITCH = 5
    PLAYSWITCH = 6

class TurnDirection(enum.Enum):
    CLOCKWISE = 1
    COUNTERCLOCKWISE = 2

# Entidades
# Estas entidades no se persisten en la BD, y por eso no están en models.py
class PlayerController():
    def __init__(self, isAI = True, user = None, player = None):
        # Hay que definir si es una IA desde el principio, el resto se puede poner luego
        if isAI is None:
            isAI = False
        self.isAI = isAI
        self.user = user
        self.player = player

class Player():
    def __init__(self, game = None, controller = None, name = None):
        self.game = game
        self.controller = controller
        self.hand = []
        self.name = name

    # Añade una carta a la mano
    def gain_card(self, card):
        if card is None:
            raise PumbaException("Card received is None")
        self.hand.append(card)

    # Elimina la carta i de la mano y la devuelve
    #def lose_card(self, index = 0):
        #return self.hand.pop(index)

class Card():
    def __init__(self, suit, number):
        if suit is None:
            raise PumbaException("Suit cannot be none")
        if number is None:
            raise PumbaException("Number cannot be none")
        self.suit = suit
        self.number = number

class Action():
    def __init__(self, type):
        if type is None:
            raise PumbaException("Type cannot be none")
        self.type = type

class Turn():
    def __init__(self):
        self.actions = []

    def add_action(self, atype):
        self.actions.append(Action(atype))

    def has(self, atype):
        for action in self.actions:
            if action.type == atype:
                return True
        return False

class Game():
    def __init__(self):
        self.status = GameStatus.WAITING
        # Suit
        self.lastSuit = None
        # CardNumbers
        self.lastNumber = None
        self.lastEffect = None
        # Integers
        self.currentPlayer = None
        self.nextPlayer = None
        # TurnDirection
        self.turnDirection = None
        # Integer
        self.drawCounter = None
        # Arrays ordenados de Card
        self.drawPile = []
        self.playPile = []
        # Jugadores de la partida
        self.players = []
        # Marcador
        self.points = []
        # User
        self.host = None
        # Turn
        self.turn = None
        self.title = "Quick game"
        self.maxPlayerCount = 4
        # Para evitar problemas de concurrencia, añadimos un cerrojo
        self.lock = False

    # Inicia una partida
    def begin_match(self, cards = None):
        if self.status is GameStatus.PLAYING:
            raise PumbaException("The game is already started!")
        if self.host is None:
            raise PumbaException("There is no defined host for the game")

        if len(self.players) < 2:
            raise PumbaException("Not enough players! " + str(len(self.players)))

        # Reinicia el estado en caso de que se esté reiniciando una partida
        self.playPile = []
        self.drawPile = []
        self.currentPlayer = 0
        self.nextPlayer = 1
        self.turnDirection = TurnDirection.CLOCKWISE
        self.drawCounter = 0
        self.turn = None
        
        # Puede aceptar una colección de cartas específica en vez de la estándar
        pile = []
        if cards is None:
            for suit in Suit:
                for number in CardNumber:
                    if number is not CardNumber.NONE:
                        card = Card(suit, number)
                        pile.append(card)
        else:
            # Para evitar posibles efectos externos copiamos la baraja
            pile = deepcopy(cards)

        # Barajamos la baraja
        random.shuffle(pile)
        # Le damos a cada jugador cuatro cartas
        for player in self.players:
            player.hand = []
            for i in range(4):
                player.gain_card(pile.pop())
        # Ponemos la primera carta en la pila de juego
        primera = pile.pop()
        self.drawPile = pile
        self.playPile.append(primera)
        self.lastSuit = primera.suit
        self.lastEffect = CardNumber.NONE
        self.lastNumber = primera.number

        # Establecemos el siguiente jugador
        self.nextPlayer = 0
        self.currentPlayer = None

        # Cambiamos el estado de juego
        self.status = GameStatus.PLAYING

        # Establecemos el sentido de los turnos
        self.turnDirection = TurnDirection.CLOCKWISE

        # Ponemos a cero el contador de robo
        self.drawCounter = 0

        # Ejecutamos el procesamiento de inicio de turno
        self.begin_turn()
            

    # Le cede el turno al siguiente jugador
    def begin_turn(self):
        if self.status is not GameStatus.PLAYING:
            raise PumbaException("The game is not started!")

        # Si no ha empezado la partida, seguimos;
        # si no, hay que asegurarse de que se puede terminar el turno
        if(self.currentPlayer is not None):
            # Si no ha jugado una carta o sido forzado a robar, comprueba que ha robado dos cartas
            # Alternativamente, contempla que no se puedan robar cartas y te deja ir
            if not (self.turn.has(ActionType.PLAYSWITCH) or self.turn.has(ActionType.PLAY) or self.turn.has(ActionType.PLAYKING) or self.turn.has(ActionType.DRAWCOUNTER) or len(self.playPile) + len(self.drawPile) == 0):
                count = 0
                for a in self.turn.actions:
                    if(a.type == ActionType.DRAW):
                        count = count + 1
                if(count < 2):
                    raise IllegalMoveException("Cannot end turn without playing or drawing cards!")

        # Ponemos al siguiente jugador
        self.currentPlayer = self.nextPlayer

        # Elegimos el siguiente jugador
        self.update_next_player(self.currentPlayer)

        # Añadimos un nuevo historial de acciones
        self.turn = Turn()

    def update_next_player(self, current):
        if self.turnDirection == TurnDirection.CLOCKWISE:
            self.nextPlayer = (current + 1) % len(self.players)
        else:
            if(current == 0):
                self.nextPlayer = len(self.players) - 1
            else:
                self.nextPlayer = current - 1
    
    # El jugador intenta robar una carta
    # Devuelve la carta robada
    def player_action_draw(self):
        if self.status is not GameStatus.PLAYING:
            raise PumbaException("The game is not started!")

        # Un jugador puede robar una carta si:
        # 1. El contador de robo está a 0
        # 2. No ha hecho otra cosa este turno que no sea robar carta una vez
        if self.drawCounter > 0:
            raise IllegalMoveException("Draw counter must be zero!")
        
        actions = self.turn.actions
        draw_count = 0
        for a in actions:
            if a.type != ActionType.DRAW:
                raise IllegalMoveException("Cannot draw if something else has been done this turn!")
            else:
                draw_count = draw_count + 1
        if (draw_count > 1):
            raise IllegalMoveException("Can only draw up to twice per turn!")

        # Roba la carta
        if(len(self.drawPile) == 0):
            # Si la baraja se ha acabado, hay que remezclar
            # Si no hay cartas en juego, no se puede robar
            if (len(self.playPile) == 0):
                raise IllegalMoveException("Cannot draw if there are no cards in play!")
            else:
                self.shuffle_play_draw()
        
        card = self.drawPile.pop()
        self.players[self.currentPlayer].gain_card(card)
        self.turn.add_action(ActionType.DRAW)
        return card

    # Roba por la pila de robo
    def player_action_draw_forced(self):
        if self.status is not GameStatus.PLAYING:
            raise PumbaException("The game is not started!")

        # Para poder hacer esta acción:
        # 1. No se puede haber hecho nada este turno
        # 2. El contador de robo no puede ser cero

        if (len(self.turn.actions) != 0):
            raise IllegalMoveException("Draw from draw counter must be done at the beginning of turn!")

        if (self.drawCounter < 1):
            raise IllegalMoveException("Cannot draw if the counter is zero already!")

        # Se roban tantas cartas como indique el contador
        # Si no hay las suficientes en juego, lo ponemos a 0 igualmente
        drawn = []
        for i in range(self.drawCounter):
            if(len(self.drawPile) == 0):
                self.shuffle_play_draw()
                if(len(self.drawPile) == 0):
                    break
            card = self.drawPile.pop()
            drawn.append(card)
            self.players[self.currentPlayer].gain_card(card)
        
        self.turn.add_action(ActionType.DRAWCOUNTER)

        self.drawCounter = 0

        return drawn

    # El jugador juega una carta
    def player_action_play(self, index):
        if self.status is not GameStatus.PLAYING:
            raise PumbaException("The game is not started!")

        if index < 0 or index -1 > len(self.players[self.currentPlayer].hand):
            raise PumbaException("Invalid card index!")

        # Hay los siguientes casos posibles para jugar una carta
        # 1. Si el contador de robo no es 0, se puede jugar solamente 1 o 2
        # 2. Si no hay un rey jugado:
        #   2.1 Debe tener el mismo palo y número
        #   2.2 No debe haber jugado otra carta el mismo turno
        # 3. Si hay un rey jugado:
        #   3.1 Debe tener el mismo palo que el rey

        # Carta a jugar
        card = self.players[self.currentPlayer].hand[index]

        # Si hay que robar carta:
        if (self.drawCounter > 0):
            if (self.turn.has(ActionType.PLAY)):
                raise IllegalMoveException("You've already played a card this turn!")
            if (card.number != CardNumber.ONE and card.number != CardNumber.TWO and not(card.number == CardNumber.COPY and card.suit == self.lastSuit)):
                raise IllegalMoveException("Must deflect card draw with One or Two!")
            
            # Quitamos la carta de la mano del jugador
            card = self.players[self.currentPlayer].hand.pop(index)

            # Ejecutamos los efectos de la carta
            self.execute_card_effect(card)
            
            # Ponemos la carta en la pila de juego
            self.playPile.append(card)
  
        # Si se ha jugado un rey:
        elif (self.turn.has(ActionType.PLAYKING)):
            # Se comprueba que la carta es del mismo palo
            if(card.suit != self.lastSuit):
                raise IllegalMoveException("This card is not of a suitable suit!")
            
            # Quitamos la carta de la mano del jugador
            card = self.players[self.currentPlayer].hand.pop(index)

            # Actualizamos el estado de juego para reflejarlo
            self.lastEffect = CardNumber.NONE
            self.lastNumber = card.number

            # Ponemos la carta en la pila de juego
            self.playPile.append(card)

        else:
            # Se comprueba que se puede jugar la carta
            if(self.lastSuit != card.suit and self.lastNumber != card.number):
                raise IllegalMoveException("That card does not share a suit or number with the last card played!")

            # Se comprueba que no se ha jugado otra carta este último turno
            if(self.turn.has(ActionType.PLAYSWITCH) or self.turn.has(ActionType.PLAY)):
                raise IllegalMoveException("You already played a card this turn!")
            
            # Quitamos la carta de la mano del jugador
            card = self.players[self.currentPlayer].hand.pop(index)

            # Ejecutamos los efectos de la carta
            self.execute_card_effect(card)

            # Ponemos la carta en la pila de juego
            self.playPile.append(card)

    def player_action_switch(self, suit):
        if self.status is not GameStatus.PLAYING:
            raise PumbaException("The game is not started!")

        if (self.turn.has(ActionType.PLAYSWITCH) and not self.turn.has(ActionType.SWITCH)):
            if (suit in Suit):
                self.lastSuit = suit
            else:
                raise ValueError("Invalid suit!")
        else:
            raise IllegalMoveException("Cannot switch!")

    def execute_card_effect(self, card):
        if (card.number == CardNumber.ONE):
            self.drawCounter = self.drawCounter + 1
            self.lastEffect = CardNumber.ONE
            self.lastNumber = CardNumber.ONE
            self.lastSuit = card.suit
            self.turn.add_action(ActionType.PLAY)
        elif (card.number == CardNumber.TWO):
            self.drawCounter = self.drawCounter + 2
            self.lastEffect = CardNumber.TWO
            self.lastNumber = CardNumber.TWO
            self.lastSuit = card.suit
            self.turn.add_action(ActionType.PLAY)
        elif (card.number == CardNumber.COPY):
            # Crea una carta temporal para copiar el efecto
            if(self.lastEffect == CardNumber.NONE):
                #self.lastNumber = CardNumber.COPY
                self.lastEffect = CardNumber.NONE
                self.lastSuit = card.suit
                #self.turn.add_action(ActionType.PLAY)
                self.execute_card_effect(Card(self.lastSuit, CardNumber.NONE))
            else:
                self.execute_card_effect(Card(self.lastSuit, self.lastEffect))
        elif (card.number == CardNumber.DIVINE):
            # El estado interno del juego no cambia; hay que gestionar el efecto
            # de forma exterior
            self.lastEffect = CardNumber.DIVINE
            self.lastNumber = CardNumber.DIVINE
            self.lastSuit = card.suit
            self.turn.add_action(ActionType.PLAY)
        elif (card.number == CardNumber.FLIP):
            self.lastEffect = CardNumber.FLIP
            self.lastNumber = CardNumber.FLIP
            self.lastSuit = card.suit
            
            if(self.turnDirection == TurnDirection.CLOCKWISE):
                self.turnDirection = TurnDirection.COUNTERCLOCKWISE
            else:
                self.turnDirection = TurnDirection.CLOCKWISE

            self.update_next_player(self.currentPlayer)
            self.turn.add_action(ActionType.PLAY)
        elif (card.number == CardNumber.JUMP):
            self.lastEffect = CardNumber.JUMP
            self.lastNumber = CardNumber.JUMP
            self.lastSuit = card.suit
            self.update_next_player(self.nextPlayer)
            self.turn.add_action(ActionType.PLAY)
        elif (card.number == CardNumber.SWITCH):
            # El estado interno del juego no cambia; hay que gestionar el efecto
            # de forma exterior
            self.lastEffect = CardNumber.SWITCH
            self.lastNumber = CardNumber.SWITCH
            self.lastSuit = card.suit
            self.turn.add_action(ActionType.PLAYSWITCH)
        elif (card.number == CardNumber.KING):
            self.lastEffect = CardNumber.KING
            self.lastNumber = CardNumber.KING
            self.lastSuit = card.suit
            self.turn.add_action(ActionType.PLAYKING)
        elif(card.number == CardNumber.NONE):
            self.lastEffect = CardNumber.NONE
            self.lastSuit = card.suit
            self.turn.add_action(ActionType.PLAY)

    # Baraja la pila de juego en la pila de robo
    def shuffle_play_draw(self):
        # Cogemos la pila de juego
        pile = self.playPile
        # La pila de juego la vaciamos
        self.playPile = []
        # Mezclamos la pila
        random.shuffle(pile)
        # La ponemos como pila de robo
        self.drawPile = pile
