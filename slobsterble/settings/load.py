"""Load settings from a configuration file."""

import configparser
import pathlib
import os


CONFIG_PATH = os.path.join(os.getenv('HOME'), '.slobsterble.conf')
DEVELOPER_PATH = os.path.join(os.path.dirname(__file__), 'developer.conf')
TESTING_PATH = os.path.join(os.path.dirname(__file__), 'testing.conf')


def load_config(settings, testing=False):
    """Load configuration."""
    config = configparser.ConfigParser()
    path = CONFIG_PATH
    config_parsed = config.read([path])
    if not config_parsed:
        path = DEVELOPER_PATH
    config = configparser.ConfigParser()
    if testing:
        path = TESTING_PATH
    config.read_file(open(path))
    sql_dialect = config.get('db', 'SQL_DIALECT')
    database_path = config.get('db', 'DATABASE_PATH')
    grandparent_path = pathlib.Path(os.path.dirname(__file__)).parent.parent
    settings.SQLALCHEMY_DATABASE_URI = sql_dialect + ':///' + os.path.join(
        grandparent_path, database_path)
    settings.SQLALCHEMY_TRACK_MODIFICATIONS = config.get(
        'db', 'SQLALCHEMY_TRACK_MODIFICATIONS')
    settings.ADMIN_USERNAME = config.get('db', 'ADMIN_USERNAME')
    settings.ADMIN_PASSWORD = config.get('db', 'ADMIN_PASSWORD')
    settings.SECRET_KEY = config.get('flask', 'SECRET_KEY')
