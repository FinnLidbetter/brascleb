"""Models related to games and players in those games."""


from sqlalchemy.orm import relationship

from slobsterble import db
from slobsterble.models.mixins import ModelMixin, ModelSerializer


rack = db.Table('rack',
                db.Column('game_player_id',
                          db.Integer,
                          db.ForeignKey('game_player.id'),
                          primary_key=True),
                db.Column('tile_count_id',
                          db.Integer,
                          db.ForeignKey('tile_count.id'),
                          primary_key=True))

board_state = db.Table('board_state',
                       db.Column('game_id',
                                 db.Integer,
                                 db.ForeignKey('game.id'),
                                 primary_key=True),
                       db.Column('played_tile_id',
                                 db.Integer,
                                 db.ForeignKey('played_tile.id'),
                                 primary_key=True))

bag_tiles = db.Table('bag_tiles',
                     db.Column('game_id',
                               db.Integer,
                               db.ForeignKey('game.id'),
                               primary_key=True),
                     db.Column('tile_count_id',
                               db.Integer,
                               db.ForeignKey('tile_count.id'),
                               primary_key=True))

WORD_LENGTH_MAX = 21


class GamePlayer(db.Model, ModelMixin, ModelSerializer):
    """A player in a game."""
    serialize_exclude_fields = ['game', 'game_id', 'player_id']

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    player_id = db.Column(db.Integer,
                          db.ForeignKey('player.id'),
                          nullable=False)
    player = relationship('Player',
                          backref=db.backref('game_players', lazy=True),
                          doc='The user for this game player.')
    rack = db.relationship(
        'TileCount',
        secondary=rack,
        lazy='subquery',
        doc='The collection of tiles currently held by this player.')
    score = db.Column(db.Integer,
                      nullable=False,
                      default=0,
                      doc='The number of points that this player has.')
    turn_order = db.Column(db.Integer,
                           nullable=False,
                           doc='A value to indicate when it is this player\'s '
                               'turn.')
    game_id = db.Column(db.Integer,
                        db.ForeignKey('game.id'),
                        nullable=False)
    game = relationship('Game',
                        backref=db.backref('game_players', lazy=True),
                        doc='The game that this player is playing in.')

    def __repr__(self):
        return '(%s) %s: %d' % (self.game, self.player, self.score)


class Game(db.Model, ModelMixin, ModelSerializer):
    """A game."""
    serialize_exclude_fields = ['dictionary_id']
    serialize_include_fields = ['num_players', 'whose_turn']

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    board_state = db.relationship(
        'PlayedTile',
        secondary=board_state,
        lazy='subquery',
        doc='The positions of the played tiles.')
    bag_tiles = db.relationship(
        'TileCount',
        secondary=bag_tiles,
        lazy='subquery',
        doc='The tiles remaining in the bag.')
    dictionary_id = db.Column(db.Integer,
                              db.ForeignKey('dictionary.id'),
                              nullable=False)
    dictionary = relationship('Dictionary',
                              doc='The dictionary being used by this game.')
    started = db.Column(db.DateTime,
                        nullable=False,
                        doc='The date and time that this game was started.')
    completed = db.Column(db.DateTime,
                          nullable=True,
                          doc='The date and time that this game was finished.')
    turn_number = db.Column(db.Integer,
                            nullable=False,
                            default=0,
                            doc='The current turn number of the game.')

    @property
    def num_players(self):
        return len(self.game_players)

    @property
    def whose_turn(self):
        turn_order_number = self.turn_number % len(self.game_players)
        for game_player in self.game_players:
            if game_player.turn_order == turn_order_number:
                return game_player.player.display_name
        return 'Unknown'


class Move(db.Model, ModelMixin, ModelSerializer):
    """A played word in a turn and its score."""
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    game_player_id = db.Column(db.Integer,
                               db.ForeignKey('game_player.id'),
                               nullable=False)
    game_player = relationship('GamePlayer',
                               backref=db.backref('moves', lazy=True),
                               doc='The player that played this move.')
    primary_word = db.Column(db.String(WORD_LENGTH_MAX), nullable=False,
                             doc='The word created along the axis on which '
                                 'multiple tiles were played. Defaults to '
                                 'the word on the horizontal axis if a '
                                 'single tile is played.')
    secondary_words = db.Column(
        db.String(WORD_LENGTH_MAX * (WORD_LENGTH_MAX + 1)),
        nullable=False,
        doc='Other words created in a single tile. Words are comma-separated.')
    turn_number = db.Column(db.Integer,
                            nullable=False,
                            doc='The turn number of the game that this move '
                                'was played.')
    score = db.Column(db.Integer,
                      nullable=False,
                      doc='The number of points scored with this move.')
    time_played = db.Column(db.DateTime,
                            nullable=False,
                            doc='The date and time that this move was played.')

    def __repr__(self):
        return '%d: %s' % (self.turn_number, self.primary_word)
