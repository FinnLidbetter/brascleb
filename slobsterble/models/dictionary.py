"""Models relating to the dictionary and playable words."""

from slobsterble import db

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


class Dictionary(db.Model):
    """A collection of words."""
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String(100),
                     unique=True,
                     nullable=False,
                     doc='User-friendly name for the dictionary.')
    entries = db.relationship(
        'Entry',
        secondary=entries,
        lazy='subquery',
        doc='The words in this dictionary.')

    def __repr__(self):
        return self.name


class Entry(db.Model):
    """A word and its definition(s)."""
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    word = db.Column(db.String(30), index=True, unique=True, nullable=False)
    definition = db.Column(
        db.Text,
        doc='Optional definition for the word. In case of '
            'multiple definitions, separate the definitions '
            'by semi-colons.')

    def __repr__(self):
        return self.word
