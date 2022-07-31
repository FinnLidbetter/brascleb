"""Initialise the Flask app."""
import logging
import os
import sys

import sqlalchemy.exc
from flask import Flask, Response
from flask_admin import Admin
from flask_login import LoginManager
from flask_mailman import Mail
from flask_migrate import Migrate
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from sqlalchemy import inspect
from werkzeug.security import generate_password_hash

import slobsterble.settings
from slobsterble.notifications import APNSManager

db = SQLAlchemy()
admin = Admin()
login_manager = LoginManager()
mail = Mail()
migrate = Migrate()
api = Api()
jwt = JWTManager()
apns = APNSManager()
logger = logging.getLogger('slobsterble')


LOG_FORMAT = '[%(asctime)s][%(levelname)s][PID-%(process)d][%(threadName)s] %(message)s'


def init_db(app):
    """Initialize the database and create the admin user."""
    db.init_app(app)
    from slobsterble.models import User
    with app.app_context():
        if inspect(db.engine).has_table('User'):
            try:
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
            except sqlalchemy.exc.OperationalError as err:
                if 'no such column: user.verified' not in str(err):
                    raise


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
    admin.add_view(
        SlobsterbleModelView(slobsterble.models.UserVerification, db.session))
    admin.init_app(app)


def init_api(app):
    from slobsterble.apis import (
        AdminLoginView,
        AdminLogoutView,
        BoardLayoutView,
        DictionaryView,
        EmailVerificationView,
        FriendsView,
        GameView,
        IndexView,
        HeadToHeadView,
        ListGamesView,
        LoginView,
        LogoutView,
        MoveHistoryView,
        NewGameView,
        PasswordResetView,
        PlayerSettingsView,
        RegisterView,
        RequestVerificationEmailView,
        RequestPasswordResetView,
        StatsView,
        TileDistributionView,
        TokenRefreshView,
        TwoLetterWordView,
        WebsiteRegisterView,
    )
    api.add_resource(IndexView, '/', '/index')
    api.add_resource(AdminLoginView, '/admin-login')
    api.add_resource(AdminLogoutView, '/admin-logout')
    api.add_resource(TokenRefreshView, '/api/refresh-access')
    api.add_resource(WebsiteRegisterView, '/site-register')
    api.add_resource(PasswordResetView, '/reset-password')
    api.add_resource(RequestVerificationEmailView, '/api/send-verification-email')
    api.add_resource(RequestPasswordResetView, '/api/request-password-reset')
    api.add_resource(RegisterView, '/api/register')
    api.add_resource(EmailVerificationView, '/api/verify')
    api.add_resource(LoginView, '/api/login')
    api.add_resource(LogoutView, '/api/logout')
    api.add_resource(BoardLayoutView, '/api/board-layout')
    api.add_resource(TileDistributionView, '/api/tile-distribution')
    api.add_resource(NewGameView, '/api/new-game')
    api.add_resource(ListGamesView, '/api/games')
    api.add_resource(GameView, '/api/game/<int:game_id>')
    api.add_resource(MoveHistoryView, '/api/game/<int:game_id>/move-history')
    api.add_resource(HeadToHeadView, '/api/head-to-head/<int:other_player_id>')
    api.add_resource(FriendsView, '/api/friends')
    api.add_resource(PlayerSettingsView, '/api/player-settings')
    api.add_resource(DictionaryView, '/api/game/<int:game_id>/verify-word/<string:word>')
    api.add_resource(TwoLetterWordView, '/api/game/<int:game_id>/two-letter-words')
    api.add_resource(StatsView, '/api/stats')
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

    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        return Response(error_string, status=401)


def init_login(app):
    """Initialize the login manager for session-based authentication."""
    from slobsterble.models import User
    login_manager.init_app(app)

    @login_manager.user_loader
    def user_loader(user_id):
        return User.query.get(int(user_id))


def init_mail(app):
    mail.init_app(app)


def init_notifications(app):
    apns.init_app(app, db)


def init_logging(app):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(app.config['LOG_LEVEL'])


def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(slobsterble.settings)

    init_logging(app)
    init_db(app)
    init_migrate(app)
    init_jwt(app)
    init_login(app)
    init_api(app)
    init_admin(app)
    init_notifications(app)
    init_mail(app)

    return app
