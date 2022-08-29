"""Management for the APNs client."""

from flask import current_app

from slobsterble.notifications.apns_client import APNsClient
from slobsterble.notifications.apns_credentials import TokenCredentials
from slobsterble.notifications.apns_exceptions import (
    APNSDeviceException,
    BadDeviceTokenException,
)
from slobsterble.notifications.config import config


class APNSManager:
    """Class to handle the connection to APNs."""

    def __init__(self, app=None, db=None):
        self.client = None
        self.fallback_sandbox_client = None
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
        self._credentials = TokenCredentials(
            auth_key_path=app.config['APNS_KEY_PATH'],
            auth_key_id=app.config['APNS_KEY_ID'],
            team_id=app.config['APNS_TEAM_ID'])
        self.client = APNsClient(
            credentials=self._credentials,
            use_sandbox=app.config['APNS_USE_SANDBOX'],
            notification_retries=app.config['APNS_NOTIFICATION_RETRIES_MAX']
        )
        if not app.config['APNS_USE_SANDBOX']:
            self.fallback_sandbox_client = APNsClient(
                credentials=self._credentials,
                use_sandbox=True,
                notification_retries=app.config['APNS_NOTIFICATION_RETRIES_MAX']
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
        self.client.reset_connection()

    def handle_unregistered_device(self, device_token):
        """Unregister the device."""
        models = {
            mapper.class_.__name__: mapper.class_
            for mapper in self.db.Model.registry.mappers
        }
        device_klass = models['Device']
        current_app.logger.info('Removing unregistered device %s.', device_token)
        unregistered_devices = self.db.session.query(device_klass).filter_by(
            device_token=device_token).all()
        for unregistered_device in unregistered_devices:
            self.db.session.remove(unregistered_device)
        self.db.session.commit()

    def notify(self, notifications):
        for notification in notifications:
            try:
                self.client.send_notification(notification, topic=config.topic)
            except BadDeviceTokenException:
                if not current_app.config['APNS_USE_SANDBOX']:
                    current_app.logger.info(
                        'Retrying notification %s to %s with sandbox.',
                        notification.payload.dict(), notification.token)
                    self.fallback_sandbox_client.send_notification(
                        notification, topic=config.topic)
                else:
                    raise
            except APNSDeviceException:
                self.handle_unregistered_device(notification.token)
