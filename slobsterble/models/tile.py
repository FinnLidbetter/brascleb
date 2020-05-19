"""Models related to information about tiles."""

from sqlalchemy.orm import relationship

from slobsterble import db
from slobsterble.models.mixins import ModelMixin


class Tile(db.Model, ModelMixin):
    """A letter and its value, possibly blank."""
    letter = db.Column(db.String(1),
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

    def __repr__(self):
        if self.is_blank:
            return '(%s)' % self.letter if self.letter else ''
        return self.letter


class TileCount(db.Model, ModelMixin):
    """A quantity of a particular tile."""
    count = db.Column(db.Integer,
                      nullable=False,
                      doc='The number of copies of the tile.')
    tile_id = db.Column(db.Integer, db.ForeignKey('tile.id'), nullable=False)
    tile = relationship('Tile', doc='The tile being copied.')

    def __repr__(self):
        return '%s x %d' % (str(self.tile), self.count)


class PlayedTile(db.Model, ModelMixin):
    """The location of a tile played on a board."""
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
