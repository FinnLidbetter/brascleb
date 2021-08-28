"""Management for the APNs client."""

from apns2.client import APNsClient
from apns2.credentials import CertificateCredentials, TokenCredentials
from flask import current_app

from slobsterble.notifications.config import config


class APNSManager:
    """Class to handle the connection to APNs."""

    def __init__(self, app=None, db=None):
        self.client = None
        self.topic = None
        self._credentials = None
        self.db = None
        if app is not None:
            self.init_app(app, db)

    def init_app(self, app, db):
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['flask-apns'] = self
        self.db = db
        self._set_default_configuration_options(app)
        if app.config.get('APNS_CERT_FILE_PATH') is not None:
            self._credentials = CertificateCredentials(app.config['APNS_CERT_FILE_PATH'])
        else:
            self._credentials = TokenCredentials(
                auth_key_path=app.config['APNS_KEY_PATH'],
                auth_key_id=app.config['APNS_KEY_ID'],
                team_id=app.config['APNS_TEAM_ID'])
        self.client = APNsClient(
            credentials=self._credentials,
            use_sandbox=app.config['APNS_USE_SANDBOX'],
            heartbeat_period=app.config['APNS_HEARTBEAT_SECONDS']
        )

    @staticmethod
    def _set_default_configuration_options(app):
        app.config.setdefault('APNS_CERT_FILE_PATH', None)
        app.config.setdefault('APNS_KEY_PATH', None)
        app.config.setdefault('APNS_KEY_ID', None)
        app.config.setdefault('APNS_TEAM_ID', None)
        app.config.setdefault('APNS_TOPIC', None)
        app.config.setdefault('APNS_HEARTBEAT_SECONDS', None)
        app.config.setdefault('APNS_USE_SANDBOX', False)
        app.config.setdefault('APNS_NOTIFICATION_RETRIES_MAX', 3)

    def refresh_client(self):
        """Reset the client."""
        current_app.logger.info('Refreshing APNs client.')
        self.client = APNsClient(
            credentials=self._credentials,
            use_sandbox=config.use_sandbox,
            heartbeat_period=config.heartbeat_seconds,
        )

    def handle_unsuccessful_notification(self, device_token, result):
        if result == 'Unregistered' or (isinstance(result, tuple) and result[0] == 'Unregistered'):
            current_app.logger.info('Removing unregistered device %s.', device_token)
            unregistered_devices = self.db.session.query('Device').filter_by(
                device_token=device_token).all()
            self.db.session.remove(unregistered_devices)
            self.db.session.commit()

    def notify(self, notifications):
        retries = 0
        should_retry = True
        while should_retry and retries < config.notification_retries_max:
            retries += 1
            should_retry = False
            try:
                results = self.client.send_notification_batch(
                    notifications=notifications, topic=config.topic
                )
                for device_token, result in results.items():
                    if result != 'Success':
                        self.handle_unsuccessful_notification(device_token, result)
            except (ConnectionResetError, BrokenPipeError) as exc:
                current_app.logger.warning('Could not reach APNs due to: %s.', str(exc))
                self.refresh_client()
                should_retry = True
