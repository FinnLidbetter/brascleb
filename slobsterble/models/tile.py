"""Models related to information about tiles."""


from sqlalchemy.orm import relationship

from slobsterble import db
from slobsterble.models.mixins import ModelMixin, ModelSerializer


class Tile(db.Model, ModelMixin, ModelSerializer):
    """A letter and its value, possibly blank."""
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    letter = db.Column(db.String(1), nullable=False)
    is_blank = db.Column(db.Boolean, nullable=False, default=False)
    value = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        if self.is_blank:
            return '(%s)' % self.letter
        return self.letter


class TileCount(db.Model, ModelMixin, ModelSerializer):
    """A quantity of a particular tile."""
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    count = db.Column(db.Integer, nullable=False)
    tile_id = db.Column(db.Integer, db.ForeignKey('tile.id'), nullable=False)
    tile = relationship('Tile')

    def __repr__(self):
        return '%s x %d' % (str(self.tile), self.count)


class PlayedTile(db.Model, ModelMixin, ModelSerializer):
    """The location of a tile played on a board."""
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    tile_id = db.Column(db.Integer, db.ForeignKey('tile.id'), nullable=False)
    tile = relationship('Tile')
    row = db.Column(db.Integer, nullable=False)
    column = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return '%s at (%d, %d)' % (str(self.tile), self.row, self.column)
