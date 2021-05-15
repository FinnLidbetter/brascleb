"""Models related to users."""

import random

from flask import current_app
from flask_login import UserMixin
from itsdangerous import (TimedJSONWebSignatureSerializer, BadSignature, SignatureExpired)
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy.orm import backref, relation, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from slobsterble.app import db
from slobsterble.constants import (
    DISPLAY_NAME_LENGTH_MAX,
    FRIEND_KEY_CHARACTERS,
    FRIEND_KEY_LENGTH,
)
from slobsterble.models.mixins import (
    MetadataMixin,
    ModelMixin,
    ModelSerializer,
)


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

friends = db.Table(
    'friends',
    db.Column('my_player_id',
              db.Integer,
              db.ForeignKey('player.id'),
              primary_key=True),
    db.Column('friend_player_id',
              db.Integer,
              db.ForeignKey('player.id'),
              primary_key=True),
    PrimaryKeyConstraint('my_player_id', 'friend_player_id'))


class User(db.Model, UserMixin, ModelMixin, ModelSerializer):
    """A user model for authentication purposes."""
    # The player attribute is an excluded backref to avoid
    # circular serialization.
    serialize_exclude_fields = ['password_hash', 'player']

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

    def generate_auth_token(self, expiration=600):
        serializer = TimedJSONWebSignatureSerializer(
            current_app.config['SECRET_KEY'], expires_in=expiration)
        return serializer.dumps({'id': self.id})

    @staticmethod
    def verify_auth_token(token):
        serializer = TimedJSONWebSignatureSerializer(current_app.config['SECRET_KEY'])
        try:
            data = serializer.loads(token)
        except SignatureExpired:
            return None  # valid token, but expired
        except BadSignature:
            return None  # invalid token
        user = User.query.get(data['id'])
        return user

    def __repr__(self):
        return self.username


class Role(db.Model, ModelMixin, ModelSerializer):
    """Model for authentication and restricting access."""
    name = db.Column(db.String(50), unique=True)


def random_friend_key():
    """Generate a 15 character string of numbers and uppercase letters."""
    return ''.join(random.choices(FRIEND_KEY_CHARACTERS, k=FRIEND_KEY_LENGTH))


class Player(db.Model, MetadataMixin, ModelSerializer):
    """Non-auth, non-game-specific information about users."""
    __tablename__ = "player"
    serialize_exclude_fields = ['game_players', 'friends', 'dictionary']

    # For some reason, defining the self-referential friends
    # column in this implementation requires having the ID field
    # directly on the model, rather than inherited from the ModelMixin.
    id = db.Column(db.Integer,
                   primary_key=True,
                   autoincrement=True,
                   doc='Integer ID for the model instance.')

    display_name = db.Column(db.String(DISPLAY_NAME_LENGTH_MAX), nullable=False)
    wins = db.Column(db.Integer, nullable=False, default=0)
    ties = db.Column(db.Integer, nullable=False, default=0)
    losses = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = relationship('User', backref=db.backref('player', uselist=False))
    highest_individual_score = db.Column(db.Integer, nullable=False, default=0)
    highest_combined_score = db.Column(db.Integer, nullable=False, default=0)
    best_word_score = db.Column(db.Integer, nullable=False, default=0)
    friend_key = db.Column(db.String(FRIEND_KEY_LENGTH), nullable=False,
                           default=random_friend_key)
    friends = relation(
        'Player',
        secondary=friends,
        primaryjoin=friends.c.my_player_id == id,
        secondaryjoin=friends.c.friend_player_id == id,
        backref=backref('friend_of'),
        doc='The set of players that a player can challenge to a game.')
    dictionary_id = db.Column(
        db.Integer, db.ForeignKey('dictionary.id'), nullable=False,
        doc='The player\'s preferred dictionary.')
    dictionary = relationship('Dictionary')

    board_layout_id = db.Column(
        db.Integer, db.ForeignKey('board_layout.id'), nullable=False,
        doc='The player\'s preferred board layout.')
    board_layout = relationship('BoardLayout')

    distribution_id = db.Column(
        db.Integer, db.ForeignKey('distribution.id'), nullable=False,
        doc='The player\'s preferred tile distribution.')
    distribution = relationship('Distribution')

    def __str__(self):
        return self.display_name

    def __repr__(self):
        return '%s (%d)' % (self.__str__(), self.id)
