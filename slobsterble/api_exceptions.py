"""Custom exceptions raised during validation of turn play."""


class BaseApiException(Exception):
    """
    Exception raised during server-side validation of a turn of the game.

    Client-side validation should make each one of these exceptions truly
    exceptional on the server.
    """
    default_message = 'Invalid data.'
    status_code = 400

    def __init__(self, message_override=None, status_code_override=None):
        message = message_override or self.default_message
        super().__init__(message)
        self.message = message
        self.status_code = status_code_override or self.status_code


class NewGameSchemaException(BaseApiException):
    """New game data does not conform to the schema."""
    default_message = 'New game data does not conform to the schema.'


class NewGameSelfOpponentException(BaseApiException):
    """The user chose themself as an opponent."""
    default_message = 'You cannot choose yourself as an opponent.'


class NewGameFriendException(BaseApiException):
    """One or more of the specified opponents is not your friend."""
    default_message = 'One or more of the given opponents is not your friend.'


class NewGameActiveGamesException(BaseApiException):
    """A user has too many active games to be allowed to start a new one."""
    default_message = 'The user has too many active games to start a new one.'


class NewGameLayoutDistributionException(BaseApiException):
    default_message = 'The user\'s board layout is too small for the ' \
                      'tile distribution.'


class PlaySchemaException(BaseApiException):
    """Turn play data does not conform to the schema."""
    default_message = 'Turn play data does not conform to the schema.'


class PlayAxisException(BaseApiException):
    """Played tiles do not lie on a single axis."""
    default_message = 'Played tiles do not lie on a single axis.'


class PlayCompleteException(BaseApiException):
    """The game must not be completed already."""
    default_message = 'Ths game is over already.'


class PlayCurrentTurnException(BaseApiException):
    """It must be the user's turn in the game for them to play."""
    default_message = 'It is not your turn.'
    status_code = 403


class PlayConnectedException(BaseApiException):
    """Played tiles are not connected to other played tiles."""
    default_message = 'Played tiles do not join onto existing played words.'


class PlayRackTilesException(BaseApiException):
    """The played tiles must exist on the user's rack."""
    default_message = 'Player played a tile that they do not have.'


class PlayOverlapException(BaseApiException):
    """The played tiles must not be in positions that are already occupied."""
    default_message = 'One or more of the positions of played tiles are ' \
                      'already occupied.'


class PlayContiguousException(BaseApiException):
    """The played tiles, together with existing tiles, must be contiguous."""
    default_message = 'Played tiles do not form contiguous words.'


class PlayDictionaryException(BaseApiException):
    """One or more of the created words is not found in the dictionary."""
    default_message = 'One or more created words are not in the dictionary.'


class PlayFirstTurnException(BaseApiException):
    """The first turn of the game must go through the centre of the board."""
    default_message = 'The first played word must go through the centre of ' \
                      'the board.'
