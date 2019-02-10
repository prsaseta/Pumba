import enum

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

class TurnDirection(enum.Enum):
    CLOCKWISE = 1
    COUNTERCLOCKWISE = 2

# Entidades
# Estas entidades no se persisten en la BD, y por eso no están en models.py
class PlayerController():
    def __init__(self, isAI = False, user = None, player = None):
        # Hay que definir si es una IA desde el principio, el resto se puede poner luego
        if isAI is None:
            isAI = False
        self.isAI = isAI
        self.user = user
        self.player = player

class Player():
    def __init__(self, game = None, controller = None):
        self.game = game
        self.controller = controller
        self.hand = []

class Card():
    def __init__(self, suit, number):
        if suit is None:
            raise ValueError("Suit cannot be none")
        if number is None:
            raise ValueError("Number cannot be none")
        self.suit = suit
        self.number = number

class Action():
    def __init__(self, type):
        if type is None:
            raise ValueError("Type cannot be none")
        self.type = type

class Turn():
    def __init__(self):
        self.actions = []

class Game():
    def __init__(self):
        self.status = GameStatus.WAITING
        self.lastSuit = None
        self.lastNumber = None
        self.lastEffect = None
        self.currentPlayer = 0
        self.nextPlayer = 1
        self.turnDirection = TurnDirection.CLOCKWISE
        self.drawCounter = 0
        self.drawPile = []
        self.playPile = []
        self.players = []
        self.turn = None
        # Para evitar problemas de concurrencia, añadimos un cerrojo
        self.lock = True

