"""Models related to information about tiles."""

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import relationship

from slobsterble.app import db
from slobsterble.models.mixins import MetadataMixin, ModelMixin, ModelSerializer
from slobsterble.models.user import Player

tile_distribution = db.Table('tile_distribution',
                             db.Column('distribution_id',
                                       db.Integer,
                                       db.ForeignKey('distribution.id'),
                                       primary_key=True),
                             db.Column('tile_count_id',
                                       db.Integer,
                                       db.ForeignKey('tile_count.id'),
                                       primary_key=True))


class Tile(db.Model, ModelMixin, ModelSerializer):
    """A letter and its value, possibly blank."""
    __tablename__ = 'tile'
    __table_args__ = (
        UniqueConstraint('letter', 'is_blank', 'value'),
    )
    letter = db.Column(db.String(1, collation='NOCASE'),
                       nullable=True,
                       doc='The letter to display on this tile (possibly '
                           'None).')
    is_blank = db.Column(db.Boolean,
                         nullable=False,
                         default=False,
                         doc='If True, this tile represents a blank tile.')
    value = db.Column(db.Integer,
                      nullable=False,
                      doc='The number of points scored by playing this tile.')

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        if self.is_blank:
            return '(%s)' % self.letter if self.letter else ''
        return self.letter


class TileCount(db.Model, ModelMixin, ModelSerializer):
    """A quantity of a particular tile."""
    __tablename__ = 'tile_count'
    __table_args__ = (
        UniqueConstraint('tile_id', 'count'),
    )
    serialize_exclude_fields = ['tile_id']

    count = db.Column(db.Integer,
                      nullable=False,
                      doc='The number of copies of the tile.')
    tile_id = db.Column(db.Integer, db.ForeignKey('tile.id'), nullable=False)
    tile = relationship('Tile', doc='The tile being copied.')

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return '%s x %d' % (self.tile.__repr__(), self.count)


class PlayedTile(db.Model, ModelMixin, ModelSerializer):
    """The location of a tile played on a board."""
    __tablename__ = 'played_tile'
    __table_args__ = (
        UniqueConstraint('tile_id', 'row', 'column'),
    )
    tile_id = db.Column(db.Integer, db.ForeignKey('tile.id'), nullable=False)
    tile = relationship('Tile', doc='The tile played.')
    row = db.Column(db.Integer,
                    nullable=False,
                    doc='The 0-based row index. The top row is row 0.')
    column = db.Column(db.Integer,
                       nullable=False,
                       doc='The 0-based column index. The left column '
                           'is column 0.')

    def __repr__(self):
        return '%s at (%d, %d)' % (str(self.tile), self.row, self.column)


class Distribution(db.Model, MetadataMixin, ModelSerializer):
    """A distribution of tiles for a game."""
    __tablename__ = 'distribution'
    __table_args__ = (
        UniqueConstraint('creator_id', 'name'),
    )

    id = db.Column(db.Integer,
                   primary_key=True,
                   autoincrement=True,
                   doc='Integer ID for the model instance.')

    name = db.Column(db.String(256), nullable=False,
                     doc='A descriptive name for an initial tile distribution.')
    creator_id = db.Column(
        db.Integer, db.ForeignKey('player.id', use_alter=True), nullable=True)
    creator = db.relationship(
        Player, primaryjoin=Player.id == creator_id, post_update=True,
        doc='The player that created this distribution.')
    players = db.relationship(
        Player, backref='distribution', primaryjoin=id == Player.distribution_id)

    tile_distribution = db.relationship(
        TileCount,
        secondary=tile_distribution,
        doc='The multi-set of tiles in the distribution.')
