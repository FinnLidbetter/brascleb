"""Initialise the Flask app."""

import os

from flask import Flask, Response
from flask_admin import Admin
from flask_migrate import Migrate
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from werkzeug.security import generate_password_hash

import slobsterble.settings

db = SQLAlchemy()
admin = Admin()
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
        SlobsterbleModelView(slobsterble.models.Role, db.session))
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
        FriendsView,
        GameView,
        IndexView,
        ListGamesView,
        LoginView,
        MoveHistoryView,
        NewGameView,
        RegisterView,
    )
    api.add_resource(IndexView, '/', '/index')
    api.add_resource(AdminLoginView, '/admin-login')
    api.add_resource(AdminLogoutView, '/admin-logout')
    api.add_resource(RegisterView, '/register')
    api.add_resource(LoginView, '/login')
    api.add_resource(NewGameView, '/new-game')
    api.add_resource(ListGamesView, '/games')
    api.add_resource(GameView, '/game/<int:game_id>')
    api.add_resource(MoveHistoryView, '/game/<int:game_id>/move-history')
    api.add_resource(FriendsView, '/friends')
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


def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(slobsterble.settings)

    init_db(app)
    init_migrate(app)
    init_jwt(app)
    init_api(app)
    init_admin(app)

    return app
