"""Models related to users."""

from sqlalchemy.orm import relationship

from slobsterble import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String)

    def __repr__(self):
        return self.email


class Player(db.Model):
    """Non-auth, non-game-specific information about users."""
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    display_name = db.Column(db.String(15), nullable=False)
    wins = db.Column(db.Integer, nullable=False, default=0)
    ties = db.Column(db.Integer, nullable=False, default=0)
    losses = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = relationship('User', backref=db.backref('player', uselist=False))
    highest_individual_score = db.Column(db.Integer, nullable=False, default=0)
    highest_combined_score = db.Column(db.Integer, nullable=False, default=0)
    best_word_score = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return self.display_name
