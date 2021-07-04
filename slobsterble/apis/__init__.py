"""API resources."""

from slobsterble.apis.admin import SlobsterbleModelView
from slobsterble.apis.auth import (
    AdminLoginView,
    AdminLogoutView,
    LoginView,
    LogoutView,
    RegisterView,
    TokenRefreshView,
    WebsiteRegisterView,
)
from slobsterble.apis.board_layout import BoardLayoutView
from slobsterble.apis.dictionary import DictionaryView
from slobsterble.apis.friends import FriendsView
from slobsterble.apis.game import GameView
from slobsterble.apis.index import IndexView
from slobsterble.apis.list_games import ListGamesView
from slobsterble.apis.move_history import MoveHistoryView
from slobsterble.apis.new_game import NewGameView
from slobsterble.apis.player_settings import PlayerSettingsView
from slobsterble.apis.tile_distribution import TileDistributionView


__all__ = [
    'AdminLoginView',
    'AdminLogoutView',
    'BoardLayoutView',
    'DictionaryView',
    'FriendsView',
    'GameView',
    'IndexView',
    'ListGamesView',
    'LoginView',
    'LogoutView',
    'MoveHistoryView',
    'NewGameView',
    'PlayerSettingsView',
    'RegisterView',
    'SlobsterbleModelView',
    'TileDistributionView',
    'TokenRefreshView',
    'WebsiteRegisterView',
]

