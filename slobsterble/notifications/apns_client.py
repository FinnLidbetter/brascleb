import collections
import json
import logging
from enum import Enum

import httpx

from slobsterble.notifications.apns_credentials import TokenCredentials
from slobsterble.notifications.apns_exceptions import (
    APNSException,
    APNSConnectionException,
    APNSServerException,
    BadDeviceTokenException,
    UnregisteredException,
    exception_class_for_reason,
)


class NotificationPriority(Enum):
    Immediate = '10'
    Delayed = '5'


class NotificationType(Enum):
    Alert = 'alert'
    Background = 'background'
    VoIP = 'voip'
    Complication = 'complication'
    FileProvider = 'fileprovider'
    MDM = 'mdm'


Notification = collections.namedtuple('Notification', ['token', 'payload'])

DEFAULT_APNS_PRIORITY = NotificationPriority.Immediate

logger = logging.getLogger(__name__)


class APNsClient:

    PROTOCOL = 'https'
    SANDBOX_SERVER = 'api.development.push.apple.com'
    LIVE_SERVER = 'api.push.apple.com'

    DEFAULT_PORT = 443
    ALTERNATIVE_PORT = 2197

    LIMITS = httpx.Limits(max_keepalive_connections=0, max_connections=1)

    def __init__(
            self,
            credentials: TokenCredentials,
            use_sandbox=False,
            use_alternative_port=False,
            notification_retries=3
    ):
        self.__credentials = credentials
        self._client = None
        server = self.SANDBOX_SERVER if use_sandbox else self.LIVE_SERVER
        port = self.ALTERNATIVE_PORT if use_alternative_port else self.DEFAULT_PORT
        self.base_url = f'{self.PROTOCOL}://{server}:{port}'
        self.notification_retries = notification_retries

    @property
    def _connection(self):
        if self._client is None:
            logger.info("Connecting to APNS server at %s", self.base_url)
            self._client = httpx.Client(base_url=self.base_url, http2=True, limits=self.LIMITS, timeout=10.0)
        return self._client

    def _reset_connection(self):
        if self._client is not None:
            logger.info("Closing connection to APNS server.")
            self._client.close()
        self._client = None

    def _build_headers(self, payload, topic=None, priority=NotificationPriority.Immediate,
                       expiration=None, collapse_id=None, push_type=None):
        headers = {}
        inferred_push_type = None
        if topic is not None:
            headers['apns-topic'] = topic
            if topic.endswith('.voip'):
                inferred_push_type = NotificationType.VoIP.value
            elif topic.endswith('.complication'):
                inferred_push_type = NotificationType.Complication.value
            elif topic.endswith('.pushkit.fileprovider'):
                inferred_push_type = NotificationType.FileProvider.value
            elif any([
                payload.alert is not None,
                payload.badge is not None,
                payload.sound is not None,
            ]):
                inferred_push_type = NotificationType.Alert.value
            else:
                inferred_push_type = NotificationType.Background.value

        if push_type:
            inferred_push_type = push_type.value

        if inferred_push_type:
            headers['apns-push-type'] = inferred_push_type

        if priority != DEFAULT_APNS_PRIORITY:
            headers['apns-priority'] = priority.value

        if expiration is not None:
            headers['apns-expiration'] = '%d' % expiration

        auth_header = self.__credentials.get_authorization_header()
        if auth_header is not None:
            headers['authorization'] = auth_header

        if collapse_id is not None:
            headers['apns-collapse-id'] = collapse_id
        return headers

    def _send_notification(self, payload, headers, device_token):
        url_path = '/3/device/{}'.format(device_token)
        data = json.dumps(payload.dict()).encode('utf-8')
        try:
            response = self._connection.post(url_path, content=data, headers=headers)
        except httpx.RequestError as e:
            logger.debug('Failed to receive a response: %s', str(e))
            raise APNSConnectionException()
        status = 'Success' if response.status_code == 200 else 'Failure'
        logger.debug('Received response: %d (%s)', response.status_code, status)

        if response.status_code != 200:
            apns_id = response.headers.get("apns-id")
            apns_data = json.loads(response.text)
            reason = apns_data['reason']
            exception_class = exception_class_for_reason(reason)
            exception_kwargs = {'status_code': response.status_code, 'apns_id': apns_id}
            if issubclass(exception_class, UnregisteredException):
                exception_kwargs['timestamp'] = apns_data['timestamp']
            raise exception_class(**exception_kwargs)

    def send_notification(
            self, notification: Notification, topic=None,
            priority=NotificationPriority.Immediate, expiration=None, collapse_id=None,
            push_type=None
    ):
        device_token = notification.token
        payload = notification.payload
        headers = self._build_headers(payload, topic, priority, expiration, collapse_id, push_type)

        logger.debug('Sending notification %s to %s.', payload.dict(), device_token)
        exc = None
        for _ in range(self.notification_retries):
            try:
                self._send_notification(payload, headers, device_token)
                exc = None
                break
            except APNSServerException as e:
                exc = e
                self._reset_connection()
            except APNSException as e:
                exc = e
                break
        if exc is not None:
            logger.exception(
                'Failed to send notification %s to %s due to %s.',
                payload.dict(), device_token, repr(exc)
            )
            if isinstance(exc, (UnregisteredException, BadDeviceTokenException)):
                raise exc
