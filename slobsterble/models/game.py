"""Models related to games and players in those games."""

from sqlalchemy import func, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.orm import relationship

from slobsterble.app import db
from slobsterble.constants import WORD_LENGTH_MAX
from slobsterble.models.mixins import ModelMixin, ModelSerializer


rack = db.Table(
    'rack',
    db.Column('game_player_id', db.Integer, db.ForeignKey('game_player.id'),
              primary_key=True),
    db.Column('tile_count_id', db.Integer, db.ForeignKey('tile_count.id'),
              primary_key=True))

move_rack_tiles = db.Table(
    'move_rack_tiles',
    db.Column('move_id', db.Integer, db.ForeignKey('move.id'),
              primary_key=True),
    db.Column('tile_count_id', db.Integer, db.ForeignKey('tile_count.id'),
              primary_key=True))

move_exchanged_tiles = db.Table(
    'move_exchanged_tiles',
    db.Column('move_id', db.Integer, db.ForeignKey('move.id'),
              primary_key=True),
    db.Column('tile_count_id', db.Integer, db.ForeignKey('tile_count.id'),
              primary_key=True))

move_played_tiles = db.Table(
    'move_played_tiles',
    db.Column('move_id', db.Integer, db.ForeignKey('move.id'),
              primary_key=True),
    db.Column('played_tile_id', db.Integer, db.ForeignKey('played_tile.id'),
              primary_key=True))

board_state = db.Table(
    'board_state',
    db.Column('game_id', db.Integer, db.ForeignKey('game.id'),
              primary_key=True),
    db.Column('played_tile_id', db.Integer, db.ForeignKey('played_tile.id'),
              primary_key=True))

bag_tiles = db.Table(
    'bag_tiles',
    db.Column('game_id', db.Integer, db.ForeignKey('game.id'),
              primary_key=True),
    db.Column('tile_count_id', db.Integer, db.ForeignKey('tile_count.id'),
              primary_key=True))


class GamePlayer(db.Model, ModelMixin, ModelSerializer):
    """A player in a game."""
    __tablename__ = 'game_player'

    __table_args__ = (
        UniqueConstraint('player_id', 'game_id'),
    )

    serialize_exclude_fields = ['game', 'game_id', 'player_id']

    player_id = db.Column(db.Integer,
                          db.ForeignKey('player.id'),
                          nullable=False)
    player = relationship('Player',
                          backref=db.backref('game_players'),
                          doc='The user for this game player.')
    rack = db.relationship(
        'TileCount',
        secondary=rack,
        doc='The collection of tiles currently held by this player.')
    score = db.Column(db.Integer,
                      nullable=False,
                      default=0,
                      doc='The number of points that this player has.')
    turn_order = db.Column(db.Integer,
                           nullable=False,
                           doc='A value to indicate when it is this player\'s '
                               'turn.')
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'))

    def __repr__(self):
        return '(%s) %s: %d' % (self.game, self.player, self.score)


class Game(db.Model, ModelMixin, ModelSerializer):
    """A game."""
    __tablename__ = 'game'

    id = db.Column(db.Integer, primary_key=True, autoincrement='ignore_fk')

    serialize_exclude_fields = ['dictionary_id',
                                'game_player_to_play_id',
                                'game_player_to_play']
    serialize_include_fields = [
        'num_players', 'whose_turn_name', 'num_tiles_remaining']

    board_state = db.relationship(
        'PlayedTile',
        secondary=board_state,
        doc='The positions of the played tiles.')
    bag_tiles = db.relationship(
        'TileCount',
        secondary=bag_tiles,
        doc='The tiles remaining in the bag.')
    dictionary_id = db.Column(db.Integer,
                              db.ForeignKey('dictionary.id'),
                              nullable=False)
    dictionary = relationship('Dictionary',
                              doc='The dictionary being used by this game.')
    board_layout_id = db.Column(db.Integer,
                                db.ForeignKey('board_layout.id'),
                                nullable=False)
    board_layout = relationship('BoardLayout',
                                doc='The board layout being used by this game.')
    initial_distribution_id = db.Column(db.Integer,
                                        db.ForeignKey('distribution.id'),
                                        nullable=False)
    initial_distribution = relationship('Distribution',
                                        doc='The initial tile distribution.')

    started = db.Column(db.DateTime,
                        default=func.utcnow(),
                        nullable=False,
                        doc='The date and time that this game was started.')
    completed = db.Column(db.DateTime,
                          nullable=True,
                          doc='The date and time that this game was finished.')
    turn_number = db.Column(db.Integer,
                            nullable=False,
                            default=0,
                            doc='The current turn number of the game.')
    game_players = relationship(
        GamePlayer,
        primaryjoin=id == GamePlayer.game_id,
        foreign_keys=GamePlayer.game_id,
        backref="game")

    @property
    def whose_turn(self):
        for game_player in self.game_players:
            if self.turn_number % len(self.game_players) == game_player.turn_order:
                return game_player

    @property
    def whose_turn_name(self):
        return self.whose_turn.player.display_name

    @property
    def num_players(self):
        return len(self.game_players)

    @property
    def num_tiles_remaining(self):
        tile_total = 0
        for tile_count in self.bag_tiles:
            tile_total += tile_count.count
        return tile_total


class Move(db.Model, ModelMixin, ModelSerializer):
    """A played word in a turn and its score."""
    game_player_id = db.Column(
        db.Integer, db.ForeignKey('game_player.id'), nullable=False)
    game_player = relationship(
        'GamePlayer', backref=db.backref('moves'),
        doc='The player that played this move.')
    primary_word = db.Column(
        db.String(WORD_LENGTH_MAX), nullable=True,
        doc='The word created along the axis on which multiple tiles were '
            'played. Defaults to the word on the horizontal axis if a single '
            'tile is played.')
    secondary_words = db.Column(
        db.String(WORD_LENGTH_MAX * (WORD_LENGTH_MAX + 1)), nullable=True,
        doc='Other words created in this turn. Words are comma-separated.')
    rack_tiles = db.relationship(
        'TileCount', secondary=move_rack_tiles,
        doc='The tiles held by the player when this move was played.')
    played_tiles = db.relationship(
        'PlayedTile', secondary=move_played_tiles,
        doc='The positions of the tiles played in this move.')
    exchanged_tiles = db.relationship(
        'TileCount', secondary=move_exchanged_tiles,
        doc='The tiles exchanged by the player in this move.')
    turn_number = db.Column(
        db.Integer, nullable=False,
        doc='The turn number of the game that this move was played.')
    score = db.Column(
        db.Integer, nullable=False,
        doc='The number of points scored with this move.')
    played_time = db.Column(
        db.DateTime, nullable=False,
        doc='The date and time that this move was played.')

    def __repr__(self):
        return '%d: %s' % (self.turn_number, self.primary_word)
