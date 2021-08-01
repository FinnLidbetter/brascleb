"""Initialise the Flask app."""

import os

from flask import Flask, Response
from flask_admin import Admin
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from werkzeug.security import generate_password_hash

import slobsterble.settings

db = SQLAlchemy()
admin = Admin()
login_manager = LoginManager()
migrate = Migrate()
api = Api()
jwt = JWTManager()


def init_db(app):
    """Initialize the database and create the admin user."""
    db.init_app(app)
    from slobsterble.models import User
    with app.app_context():
        if db.engine.dialect.has_table(db.engine, 'User'):
            admin_user_exists = User.query.filter_by(
                username=app.config['ADMIN_USERNAME']).one_or_none() is not None
            if not admin_user_exists:
                admin_user = User(
                    username=app.config['ADMIN_USERNAME'],
                    password_hash=generate_password_hash(
                        app.config['ADMIN_PASSWORD']),
                    activated=True)
                db.session.add(admin_user)
                db.session.commit()


def init_migrate(app):
    """
    Initialize flask_migrate.

    This assumes that the database has been initialised already.
    """
    migrate.init_app(
        app=app, db=db, directory=os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
            'alembic'), compare_type=True)


def init_admin(app):
    """Initialise model views."""
    import slobsterble.models
    from slobsterble.apis import SlobsterbleModelView
    admin.add_view(
        SlobsterbleModelView(slobsterble.models.BoardLayout, db.session))
    admin.add_view(
        SlobsterbleModelView(slobsterble.models.Device, db.session))
    admin.add_view(
        SlobsterbleModelView(slobsterble.models.Dictionary, db.session))
    admin.add_view(
        SlobsterbleModelView(slobsterble.models.Distribution, db.session))
    admin.add_view(
        SlobsterbleModelView(slobsterble.models.Entry, db.session))
    admin.add_view(
        SlobsterbleModelView(slobsterble.models.Game, db.session))
    admin.add_view(
        SlobsterbleModelView(slobsterble.models.GamePlayer, db.session))
    admin.add_view(
        SlobsterbleModelView(slobsterble.models.Modifier, db.session))
    admin.add_view(
        SlobsterbleModelView(slobsterble.models.Move, db.session))
    admin.add_view(
        SlobsterbleModelView(slobsterble.models.PositionedModifier, db.session))
    admin.add_view(
        SlobsterbleModelView(slobsterble.models.Tile, db.session))
    admin.add_view(
        SlobsterbleModelView(slobsterble.models.TileCount, db.session))
    admin.add_view(
        SlobsterbleModelView(slobsterble.models.PlayedTile, db.session))
    admin.add_view(
        SlobsterbleModelView(slobsterble.models.Player, db.session))
    admin.add_view(
        SlobsterbleModelView(slobsterble.models.User, db.session))
    admin.init_app(app)


def init_api(app):
    from slobsterble.apis import (
        AdminLoginView,
        AdminLogoutView,
        BoardLayoutView,
        DictionaryView,
        FriendsView,
        GameView,
        IndexView,
        ListGamesView,
        LoginView,
        LogoutView,
        MoveHistoryView,
        NewGameView,
        PlayerSettingsView,
        RegisterView,
        TileDistributionView,
        TokenRefreshView,
        WebsiteRegisterView,
    )
    api.add_resource(IndexView, '/', '/index')
    api.add_resource(AdminLoginView, '/admin-login')
    api.add_resource(AdminLogoutView, '/admin-logout')
    api.add_resource(TokenRefreshView, '/api/refresh-access')
    api.add_resource(WebsiteRegisterView, '/site-register')
    api.add_resource(RegisterView, '/api/register')
    api.add_resource(LoginView, '/api/login')
    api.add_resource(LogoutView, '/api/logout')
    api.add_resource(BoardLayoutView, '/api/board-layout')
    api.add_resource(TileDistributionView, '/api/tile-distribution')
    api.add_resource(NewGameView, '/api/new-game')
    api.add_resource(ListGamesView, '/api/games')
    api.add_resource(GameView, '/api/game/<int:game_id>')
    api.add_resource(MoveHistoryView, '/api/game/<int:game_id>/move-history')
    api.add_resource(FriendsView, '/api/friends')
    api.add_resource(PlayerSettingsView, '/api/player-settings')
    api.add_resource(DictionaryView, '/api/game/<int:game_id>/verify-word/<string:word>')
    api.init_app(app)


def init_jwt(app):
    from slobsterble.models import User
    jwt.init_app(app)

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        return User.query.filter_by(id=identity).one_or_none()

    @jwt.user_identity_loader
    def user_identity_callback(user):
        return user.id

    @jwt.unauthorized_loader
    def unauthorized_access_callback(error_string):
        return Response(error_string, status=401)


def init_login(app):
    """Initialize the login manager for session-based authentication."""
    from slobsterble.models import User
    login_manager.init_app(app)

    @login_manager.user_loader
    def user_loader(user_id):
        return User.query.get(int(user_id))


def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(slobsterble.settings)

    init_db(app)
    init_migrate(app)
    init_jwt(app)
    init_login(app)
    init_api(app)
    init_admin(app)

    return app
