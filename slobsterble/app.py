"""Initialise the Flask app."""

import os

from flask import Flask
from flask_admin import Admin
from flask_httpauth import HTTPBasicAuth
from flask_migrate import Migrate
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

import slobsterble.settings
from slobsterble.utilities import SlobsterbleModelView

db = SQLAlchemy()
admin = Admin()
migrate = Migrate()
auth = HTTPBasicAuth()
api = Api()


def init_db(app):
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
    Initialise flask_migrate.

    This assumes that the database has been initialised already.
    """
    migrate.init_app(
        app=app, db=db, directory=os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
            'alembic'), compare_type=True)


def init_admin(app):
    """Initialise model views."""
    import slobsterble.models
    admin.init_app(app)
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


def init_blueprints(app):
    """Register blueprints with the app."""
    from slobsterble import auth, views, game_play_views
    app.register_blueprint(auth.bp)
    app.register_blueprint(views.bp)
    app.register_blueprint(game_play_views.bp)


def init_api(app):
    from slobsterble.apis import Auth, Game
    api.init_app(app)
    api.add_resource(Auth, '/auth')
    api.add_resource(Game, '/game/<int:game_id>')


def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(slobsterble.settings)

    init_db(app)
    init_migrate(app)
    init_blueprints(app)
    init_api(app)

    return app
