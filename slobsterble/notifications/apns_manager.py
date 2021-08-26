"""Management for the APNs client."""

from apns2.client import APNsClient
from apns2.credentials import CertificateCredentials, TokenCredentials


class APNSManager:
    """Class to handle the connection to APNs."""

    def __init__(self, app=None):
        self.client = None
        self.topic = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['flask-apns'] = self

        self._set_default_configuration_options(app)
        if app.config.get('APNS_CERT_FILE_PATH') is not None:
            credentials = CertificateCredentials(app.config['APNS_CERT_FILE_PATH'])
        else:
            credentials = TokenCredentials(
                auth_key_path=app.config['APNS_KEY_PATH'],
                auth_key_id=app.config['APNS_KEY_ID'],
                team_id=app.config['APNS_TEAM_ID'])
        self.client = APNsClient(credentials=credentials, use_sandbox=app.config['APNS_USE_SANDBOX'])
        self.topic = app.config['APNS_TOPIC']

    @staticmethod
    def _set_default_configuration_options(app):
        app.config.setdefault('APNS_CERT_FILE_PATH', None)
        app.config.setdefault('APNS_KEY_PATH', None)
        app.config.setdefault('APNS_KEY_ID', None)
        app.config.setdefault('APNS_TEAM_ID', None)
        app.config.setdefault('APNS_TOPIC', None)
        app.config.setdefault('APNS_USE_SANDBOX', False)
