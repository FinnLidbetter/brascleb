import click
from flask import Flask, render_template
from flask.cli import with_appcontext
from flask_admin import Admin
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

import slobsterble.settings
from slobsterble.utilities import SlobsterbleModelView

db = SQLAlchemy()
admin = Admin()
login_manager = LoginManager()


def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_object(slobsterble.settings)

    # Initialize Flask-SQLAlchemy and the init-db command.
    db.init_app(app)
    app.cli.add_command(init_db_command)

    login_manager.init_app(app)

    # Add admin model views.
    from slobsterble.models import (
        Dictionary,
        Entry,
        Game,
        GamePlayer,
        Move,
        PlayedTile,
        Player,
        Role,
        Tile,
        TileCount,
        User,
    )
    admin.init_app(app)
    admin.add_view(SlobsterbleModelView(Dictionary, db.session))
    admin.add_view(SlobsterbleModelView(Entry, db.session))
    admin.add_view(SlobsterbleModelView(Game, db.session))
    admin.add_view(SlobsterbleModelView(GamePlayer, db.session))
    admin.add_view(SlobsterbleModelView(Move, db.session))
    admin.add_view(SlobsterbleModelView(Role, db.session))
    admin.add_view(SlobsterbleModelView(Tile, db.session))
    admin.add_view(SlobsterbleModelView(TileCount, db.session))
    admin.add_view(SlobsterbleModelView(PlayedTile, db.session))
    admin.add_view(SlobsterbleModelView(Player, db.session))
    admin.add_view(SlobsterbleModelView(User, db.session))

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

    # Apply the blueprints to the app.
    from slobsterble import auth
    from slobsterble import views

    app.register_blueprint(auth.bp)
    app.register_blueprint(views.bp)

    def index():
        return render_template('index.html', title='Slobsterble')
    app.add_url_rule('/', endpoint='index', view_func=index)
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
