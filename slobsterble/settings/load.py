"""Load settings from a configuration file."""

import configparser
import datetime
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
        config = configparser.ConfigParser()
    print('Reading config from ' + path)
    config.read_file(open(path))
    sql_dialect = config.get('db', 'SQL_DIALECT')
    database_path = config.get('db', 'DATABASE_PATH')
    grandparent_path = pathlib.Path(os.path.dirname(__file__)).parent.parent
    settings.SQLALCHEMY_DATABASE_URI = sql_dialect + ':///' + os.path.join(
        grandparent_path, database_path)
    settings.SQLALCHEMY_TRACK_MODIFICATIONS = config.get(
        'db', 'SQLALCHEMY_TRACK_MODIFICATIONS')
    settings.SQLALCHEMY_ECHO = config.getboolean('db', 'SQLALCHEMY_ECHO')
    settings.ADMIN_USERNAME = config.get('db', 'ADMIN_USERNAME')
    settings.ADMIN_PASSWORD = config.get('db', 'ADMIN_PASSWORD')
    settings.SECRET_KEY = config.get('flask', 'SECRET_KEY')
    settings.JWT_SECRET_KEY = config.get('jwt', 'JWT_SECRET_KEY')
    settings.JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(
        seconds=config.getint('jwt', 'JWT_ACCESS_TOKEN_EXPIRE_SECONDS'))
    settings.JWT_REFRESH_TOKEN_EXPIRES = datetime.timedelta(
        hours=config.getfloat('jwt', 'JWT_REFRESH_TOKEN_EXPIRE_HOURS'))
    settings.JWT_COOKIE_SECURE = config.getboolean('jwt', 'JWT_COOKIE_SECURE')
    settings.JWT_TOKEN_LOCATION = config.get('jwt', 'JWT_TOKEN_LOCATION').split(',')
