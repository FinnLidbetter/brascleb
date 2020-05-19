"""Models related to users."""

from flask_login import UserMixin
from sqlalchemy.orm import relationship
from werkzeug.security import check_password_hash, generate_password_hash

from slobsterble import db, login_manager
from slobsterble.models.mixins import ModelMixin


user_roles = db.Table(
    'user_roles',
    db.Column('user_id',
              db.Integer,
              db.ForeignKey('user.id'),
              primary_key=True),
    db.Column('role_id',
              db.Integer,
              db.ForeignKey('role.id'),
              primary_key=True))

# Allow flask_login to load users.
@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


class User(db.Model, UserMixin, ModelMixin):
    """A user model for authentication purposes."""
    activated = db.Column(db.Boolean(), nullable=False, default=False)
    username = db.Column(db.String(255, collation='NOCASE'),
                         unique=True,
                         nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    roles = db.relationship('Role', secondary=user_roles)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return self.username


class Role(db.Model, ModelMixin):
    """Model for authentication and restricting access."""
    name = db.Column(db.String(50), unique=True)


class Player(db.Model, ModelMixin):
    """Non-auth, non-game-specific information about users."""
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
