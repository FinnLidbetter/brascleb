"""Package for loading system settings."""

import sys

from slobsterble.settings.load import load_config

_TEST_PROGRAMS = (
    'nosetest',
    'setup.py'
)

TESTING = False
if any(name in sys.argv[0] for name in _TEST_PROGRAMS):
    TESTING = True

ADMIN_USERNAME = None
ADMIN_PASSWORD = None

SECRET_KEY = None

SQL_DIALECT = None
DATABASE_PATH = None
SQLALCHEMY_TRACK_MODIFICATIONS = None

load_config(sys.modules[__name__], testing=TESTING)
