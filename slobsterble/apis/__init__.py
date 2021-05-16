"""API resources."""

from slobsterble.apis.auth import AdminLoginView, AdminLogoutView, LoginView, RegisterView
from slobsterble.apis.index import IndexView
from slobsterble.apis.game import GameView


__all__ = [
    'AdminLoginView',
    'AdminLogoutView',
    'GameView',
    'IndexView',
    'LoginView',
    'RegisterView',
]

