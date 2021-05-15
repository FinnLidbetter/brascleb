"""Custom exceptions raised during validation of turn play."""


class BasePlayException(Exception):
    """
    Exception raised during server-side validating a turn of the game.

    Client-side validation should make each one of these exceptions truly
    exceptional on the server.
    """
    default_message = 'Invalid play data.'
    status_code = 400

    def __init__(self, message_override=None, status_code_override=None):
        message = message_override or self.default_message
        super().__init__(message)
        self.message = message
        self.status_code = status_code_override or self.status_code


class PlaySchemaException(BasePlayException):
    """Turn play data does not conform to the schema."""
    default_message = 'Turn play data does not conform to the schema.'


class PlayLetterlessException(BasePlayException):
    """Play data contains a blank played tile with no chosen letter."""
    default_message = 'A blank tile was played with an undefined letter.'


class PlayExchangeException(BasePlayException):
    """Play data contains a mix of exchanged tiles and played tiles."""
    default_message = 'Play data contains an invalid exchanged tile.'


class PlayAxisException(BasePlayException):
    """Played tiles do not lie on a single axis."""
    default_message = 'Played tiles do not lie on a single axis.'


class PlayCurrentTurnException(BasePlayException):
    """It must be the user's turn in the game for them to play."""
    default_message = 'It is not your turn.'
    status_code = 403


class PlayConnectedException(BasePlayException):
    """Played tiles are not connected to other played tiles."""
    default_message = 'Played tiles do not join onto existing played words.'


class PlayRackTilesException(BasePlayException):
    """The played tiles must exist on the user's rack."""
    default_message = 'Player played a tile that they do not have.'


class PlayOverlapException(BasePlayException):
    """The played tiles must not be in positions that are already occupied."""
    default_message = 'One or more of the positions of played tiles are ' \
                      'already occupied.'


class PlayContiguousException(BasePlayException):
    """The played tiles, together with existing tiles, must be contiguous."""
    default_message = 'Played tiles do not form contiguous words.'


class PlayDictionaryException(BasePlayException):
    """One or more of the created words is not found in the dictionary."""
    default_message = 'One or more created words are not in the dictionary.'


class PlayFirstTurnException(BasePlayException):
    """The first turn of the game must go through the centre of the board."""
    default_message = 'The first played word must go through the centre of ' \
                      'the board.'
