from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import relationship, validates

from slobsterble import db
from slobsterble.models.mixins import ModelMixin, ModelSerializer


modifiers = db.Table('modifiers',
                     db.Column('board_layout_id',
                               db.Integer,
                               db.ForeignKey('board_layout.id'),
                               primary_key=True),
                     db.Column('positioned_modifier_id',
                               db.Integer,
                               db.ForeignKey('positioned_modifier.id'),
                               primary_key=True))


class Modifier(db.Model, ModelMixin, ModelSerializer):
    """Multiplicative modifier descriptor for played tiles."""
    __tablename__ = 'modifier'
    __table_args__ = (
        UniqueConstraint('letter_multiplier', 'word_multiplier'),
    )
    letter_multiplier = db.Column(db.Integer, nullable=False, default=1)
    word_multiplier = db.Column(db.Integer, nullable=False, default=1)

    def __repr__(self):
        if self.word_multiplier == 1 and self.letter_multiplier == 1:
            return 'None'
        if self.word_multiplier == 1:
            return '%dL' % self.letter_multiplier
        if self.letter_multiplier == 1:
            return '%dW' % self.word_multiplier
        return '%dW,%dL' % (self.word_multiplier, self.letter_multiplier)


class PositionedModifier(db.Model, ModelMixin, ModelSerializer):
    """Location of a modifier for a layout."""
    __tablename__ = 'positioned_modifier'
    __table_args__ = (
        UniqueConstraint('row', 'column', 'modifier_id'),
    )

    row = db.Column(
        db.Integer,
        nullable=False,
        doc='The 0-indexed row number of the position.')
    column = db.Column(
        db.Integer,
        nullable=False,
        doc='The 0-indexed column number of the position.')
    modifier_id = db.Column(db.Integer, nullable=False)
    modifier = relationship(
        Modifier,
        primaryjoin=modifier_id == Modifier.id,
        foreign_keys=modifier_id,
        post_update=True,
        doc='The multiplier(s) to apply at the position.')

    def __repr__(self):
        return '%s at (%d, %d)' % (str(self.modifier), self.row, self.column)


class BoardLayout(db.Model, ModelMixin, ModelSerializer):
    """A description for an empty board."""
    name = db.Column(db.String(256), nullable=False, unique=True,
                     doc='A descriptive name for the board layout.')

    rows = db.Column(
        db.Integer,
        nullable=False,
        doc='The number of rows in the layout.')

    columns = db.Column(
        db.Integer,
        nullable=False,
        doc='The number of columns in the layout.')

    modifiers = relationship(
        'PositionedModifier',
        secondary=modifiers,
        doc='The locations and types of modifiers.')

    @validates('rows')
    def validate_rows(self, key, rows):
        """Require that the number of rows is odd."""
        if rows % 2 == 0:
            raise ValueError('The number of rows must be odd.')
        return rows

    @validates('columns')
    def validate_columns(self, key, columns):
        """Require that the number of columns is odd."""
        if columns % 2 == 0:
            raise ValueError('The number of columns must be odd.')
        return columns
