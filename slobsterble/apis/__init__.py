"""API resources."""

from slobsterble.apis.admin import SlobsterbleModelView
from slobsterble.apis.auth import (
    AdminLoginView,
    AdminLogoutView,
    LoginView,
    RegisterView,
)
from slobsterble.apis.friends import FriendsView
from slobsterble.apis.game import GameView, MoveHistoryView
from slobsterble.apis.index import IndexView
from slobsterble.apis.new_game import NewGameView


__all__ = [
    'AdminLoginView',
    'AdminLogoutView',
    'FriendsView',
    'GameView',
    'IndexView',
    'LoginView',
    'MoveHistoryView',
    'NewGameView',
    'RegisterView',
    'SlobsterbleModelView',
]

