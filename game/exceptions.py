# Superclase de las excepciones a medida que defino
class PumbaException(Exception):
    pass

# Ocurre si un Game se intenta modificar mientras ya está operando
class ConcurrencyError(PumbaException):
    pass

# Ocurre si se intenta hacer una jugada ilegal
class IllegalMoveException(PumbaException):
    pass