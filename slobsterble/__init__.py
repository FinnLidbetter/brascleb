import os

import click
from flask import Flask
from flask.cli import with_appcontext
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
admin = Admin()


def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    # Some deploy systems set the database url in the environ.
    db_url = os.environ.get("DATABASE_URL")

    if db_url is None:
        # Default to a sqlite database in the instance folder.
        db_url = 'sqlite:///' + os.path.join(app.instance_path,
                                             'slobsterble.sqlite')
        # Ensure the instance folder exists.
        os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_mapping(
        # Default secret that should be overridden in environ or config.
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        SQLALCHEMY_DATABASE_URI=db_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing.
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in.
        app.config.update(test_config)

    # Initialize Flask-SQLAlchemy and the init-db command.
    db.init_app(app)
    app.cli.add_command(init_db_command)

    # Add admin model views.
    from slobsterble.models import (
        Dictionary,
        Entry,
        Game,
        GamePlayer,
        Move,
        PlayedTile,
        Player,
        Tile,
        TileCount,
        User,
    )
    admin.init_app(app)
    admin.add_view(ModelView(Game, db.session))
    admin.add_view(ModelView(GamePlayer, db.session))
    admin.add_view(ModelView(Move, db.session))
    admin.add_view(ModelView(Tile, db.session))
    admin.add_view(ModelView(TileCount, db.session))
    admin.add_view(ModelView(PlayedTile, db.session))
    admin.add_view(ModelView(User, db.session))
    admin.add_view(ModelView(Player, db.session))
    admin.add_view(ModelView(Dictionary, db.session))
    admin.add_view(ModelView(Entry, db.session))

    # Apply the blueprints to the app.
    from slobsterble import auth

    app.register_blueprint(auth.bp)

    # Make "index" point at "/", which is handled by "blog.index"
    app.add_url_rule('/', endpoint='index')
    return app


def init_db():
    db.drop_all()
    db.create_all()


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')
