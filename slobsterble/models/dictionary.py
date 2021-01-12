"""Models relating to the dictionary and playable words."""

from slobsterble import db
from slobsterble.models.mixins import ModelMixin, ModelSerializer

entries = db.Table(
    'entries',
    db.Column('entry_id',
              db.Integer,
              db.ForeignKey('entry.id'),
              primary_key=True),
    db.Column('dictionary_id',
              db.Integer,
              db.ForeignKey('dictionary.id'),
              primary_key=True))


class Dictionary(db.Model, ModelMixin, ModelSerializer):
    """A collection of words."""
    name = db.Column(db.String(100),
                     unique=True,
                     nullable=False,
                     doc='User-friendly name for the dictionary.')
    entries = db.relationship(
        'Entry',
        secondary=entries,
        doc='The words in this dictionary.')

    def __repr__(self):
        return self.name


class Entry(db.Model, ModelMixin, ModelSerializer):
    """A word and its definition(s)."""
    word = db.Column(db.String(30, collation='NOCASE'), index=True,
                     unique=True, nullable=False)
    definition = db.Column(
        db.Text,
        nullable=True,
        doc='Optional definition for the word. In case of '
            'multiple definitions, separate the definitions '
            'by semi-colons.')

    def __repr__(self):
        return self.word
