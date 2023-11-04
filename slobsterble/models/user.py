"""Models related to users."""

import random

from flask_login import UserMixin
from sqlalchemy import func, PrimaryKeyConstraint, UniqueConstraint
from sqlalchemy.orm import backref, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from slobsterble.app import db
from slobsterble.constants import (
    DISPLAY_NAME_LENGTH_MAX,
    FRIEND_KEY_CHARACTERS,
    FRIEND_KEY_LENGTH,
    UDID_MAX_LENGTH,
)
from slobsterble.models.mixins import (
    MetadataMixin,
    ModelMixin,
    ModelSerializer,
)


friends = db.Table(
    "friends",
    db.Column("my_player_id", db.Integer, db.ForeignKey("player.id"), primary_key=True),
    db.Column(
        "friend_player_id", db.Integer, db.ForeignKey("player.id"), primary_key=True
    ),
    PrimaryKeyConstraint("my_player_id", "friend_player_id"),
)


class User(db.Model, UserMixin, ModelMixin, ModelSerializer):
    """A user model for authentication purposes."""

    # The player attribute is an excluded backref to avoid
    # circular serialization.
    serialize_exclude_fields = ["password_hash", "player"]

    activated = db.Column(db.Boolean, nullable=False, default=False)
    verified = db.Column(db.Boolean, nullable=False, default=False)
    delete_requested = db.Column(db.Boolean, nullable=False, default=False)
    username = db.Column(
        db.String(255, collation="NOCASE"), unique=True, nullable=False
    )
    refresh_token_iat = db.Column(
        db.Integer,
        nullable=True,
        default=None,
        doc="Initialization timestamp of the user's most recent refresh "
        "token. Contains None if the user has manually logged out or has "
        "never logged in.",
    )
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return self.username


class UserVerification(db.Model, ModelMixin, ModelSerializer):
    """Model to track and manage email verification and password resets."""

    __tablename__ = "user_verification"

    serialize_exclude_fields = ["token_hash"]

    username = db.Column(
        db.String(255, collation="NOCASE"),
        nullable=False,
        doc="The username of the associated user.",
    )
    token_hash = db.Column(
        db.String(255),
        nullable=False,
        doc="The hash of the token sent to the user in the reset link.",
    )
    expiration_timestamp = db.Column(
        db.Integer,
        nullable=False,
        doc="The expiration timestamp for the verification link.",
    )
    used = db.Column(
        db.Boolean,
        nullable=False,
        doc="Value to indicate whether or not the corresponding token has "
        "been used.",
    )


def random_friend_key():
    """Generate a 15 character string of numbers and uppercase letters."""
    return "".join(random.choices(FRIEND_KEY_CHARACTERS, k=FRIEND_KEY_LENGTH))


class Player(db.Model, MetadataMixin, ModelSerializer):
    """Non-auth, non-game-specific information about users."""

    __tablename__ = "player"
    serialize_exclude_fields = ["game_players", "friends", "dictionary"]

    # For some reason, defining the self-referential friends
    # column in this implementation requires having the ID field
    # directly on the model, rather than inherited from the ModelMixin.
    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
        doc="Integer ID for the model instance.",
    )

    display_name = db.Column(db.String(DISPLAY_NAME_LENGTH_MAX), nullable=False)
    wins = db.Column(db.Integer, nullable=False, default=0)
    ties = db.Column(db.Integer, nullable=False, default=0)
    losses = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = relationship("User", backref=db.backref("player", uselist=False))
    highest_individual_score = db.Column(db.Integer, nullable=False, default=0)
    highest_combined_score = db.Column(db.Integer, nullable=False, default=0)
    best_word_score = db.Column(db.Integer, nullable=False, default=0)
    friend_key = db.Column(
        db.String(FRIEND_KEY_LENGTH), nullable=False, default=random_friend_key
    )
    friends = relationship(
        "Player",
        secondary=friends,
        primaryjoin=friends.c.my_player_id == id,
        secondaryjoin=friends.c.friend_player_id == id,
        backref=backref("friend_of"),
        doc="The set of players that a player can challenge to a game.",
    )
    dictionary_id = db.Column(
        db.Integer,
        db.ForeignKey("dictionary.id"),
        nullable=False,
        doc="The player's preferred dictionary.",
    )
    dictionary = relationship("Dictionary")

    board_layout_id = db.Column(
        db.Integer,
        db.ForeignKey("board_layout.id"),
        nullable=False,
        doc="The player's preferred board layout.",
    )

    distribution_id = db.Column(
        db.Integer,
        db.ForeignKey("distribution.id"),
        nullable=False,
        doc="The player's preferred tile distribution.",
    )

    def __str__(self):
        return self.display_name

    def __repr__(self):
        return "%s (%d)" % (self.__str__(), self.id)


class Device(db.Model, ModelMixin, ModelSerializer):
    """Model to associate devices with users."""

    __tablename__ = "device"

    __table_args__ = (UniqueConstraint("user_id", "device_token"),)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
    )
    user = relationship(
        "User",
        backref=db.backref("devices", cascade="all,delete"),
        doc="The user associated with this device.",
    )
    device_token = db.Column(
        db.String(UDID_MAX_LENGTH), nullable=False, doc="The device identifier."
    )
    refreshed = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="The most recent time that the user logged in with this device.",
    )
    is_sandbox_token = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        doc="If true then do not attempt to send notifications to via the "
        "production APNs server.",
    )
