"""API resources."""

from slobsterble.apis.admin import SlobsterbleModelView
from slobsterble.apis.auth import (
    AdminLoginView,
    AdminLogoutView,
    LoginView,
    RegisterView,
)
from slobsterble.apis.friends import FriendsView
from slobsterble.apis.game import GameView
from slobsterble.apis.index import IndexView
from slobsterble.apis.list_games import ListGamesView
from slobsterble.apis.move_history import MoveHistoryView
from slobsterble.apis.new_game import NewGameView


__all__ = [
    'AdminLoginView',
    'AdminLogoutView',
    'FriendsView',
    'GameView',
    'IndexView',
    'ListGamesView',
    'LoginView',
    'MoveHistoryView',
    'NewGameView',
    'RegisterView',
    'SlobsterbleModelView',
]

