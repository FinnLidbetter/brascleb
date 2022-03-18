import pytz
from datetime import datetime


# BASE

class APNSException(Exception):
    """The base class for all exceptions."""

    def __init__(self, status_code, apns_id):
        super().__init__()

        # The HTTP status code retuened by APNs.
        # A 200 value indicates that the notification was successfully sent.
        # For a list of other possible status codes, see table 6-4 in the Apple Local
        # and Remote Notification Programming Guide.
        self.status_code = status_code

        # The APNs ApnsID value from the Notification. If you didn't set an ApnsID on the
        # Notification, this will be a new unique UUID which has been created by APNs.
        self.apns_id = apns_id


class APNSDeviceException(APNSException):
    """
    Device should be flagged as potentially invalid.

    Remove immediately in case of UnregisteredException.
    """


class APNSServerException(APNSException):
    """Try again later."""


class APNSProgrammingException(APNSException):
    """Check your code, and try again later."""


# CONNECTION

class APNSConnectionException(APNSServerException):
    """Used when a connectinon to APNS servers fails."""

    def __init__(self):
        super().__init__(status_code=None, apns_id=None)


# APNS REASONS

class BadCollapseIdException(APNSProgrammingException):
    """The collapse identifier exceeds the maximum allowed size."""


class BadDeviceTokenException(APNSDeviceException):
    """
    The specified device token was bad.

    Verify that the request contains a valid token and that the token
    matches the environment.
    """


class BadExpirationDateException(APNSProgrammingException):
    """The apns-expiration value is bad."""


class BadMessageIdException(APNSProgrammingException):
    """The apns-id value is bad."""


class BadPriorityException(APNSProgrammingException):
    """The apns-priority value is bad."""


class BadTopicException(APNSProgrammingException):
    """The apns-topic was invalid."""


class DeviceTokenNotForTopicException(APNSDeviceException):
    """The device token does not match the specified topic."""


class DuplicateHeadersException(APNSProgrammingException):
    """One or more headers were repeated."""


class IdleTimeoutException(APNSServerException):
    """Idle time out."""


class InvalidPushTypeException(APNSProgrammingException):
    """The apns-push-type value is invalid."""


class MissingDeviceTokenException(APNSProgrammingException):
    """
    The device token is not specified in the request :path.

    Verify that the :path header contains the device token.
    """


class MissingTopicException(APNSProgrammingException):
    """
    The apns-topic header of the request was not specified and was required.

    The apns-topic header is mandatory when the client is connected using a
    certificate that supports multiple topics.
    """


class PayloadEmptyException(APNSProgrammingException):
    """The message payload was empty."""


class TopicDisallowedException(APNSProgrammingException):
    """Pushing to this topic is not allowed."""


class BadCertificateException(APNSProgrammingException):
    """The certificate was bad."""


class BadCertificateEnvironmentException(APNSProgrammingException):
    """The client certificate was for the wrong environment."""


class ExpiredProviderTokenException(APNSServerException):
    """
    The provider token is stale and a new token should be generated.
    """


class ForbiddenException(APNSProgrammingException):
    """The specified action is not allowed."""


class InvalidProviderTokenException(APNSProgrammingException):
    """The provider token is not valid or the token signature could not be verified."""


class MissingProviderTokenException(APNSProgrammingException):
    """
    No authentication provided.

    No provider certificate was used to connect to APNs and Authorization header
    was missing or no provider token was specified.
    """


class BadPathException(APNSProgrammingException):
    """The request contained a bad :path value."""


class MethodNotAllowedException(APNSProgrammingException):
    """The specified :method was not POST."""


class UnregisteredException(APNSDeviceException):
    """
    The device token is inactive for the specified topic.

    Expected HTTP/2 status code is 410; see Table 8-4.
    """

    def __init__(self, status_code, apns_id, timestamp):
        super().__init__(status_code=status_code, apns_id=apns_id)

        # If the value of StatusCode is 410, this is the last time at which APNs
        # confirmed that the device token was no longer valid for the topic.
        # The value is in milliseconds (ms).
        self.timestamp = timestamp

    @property
    def timestamp_datetime(self):
        if not self.timestamp:
            return None
        return datetime.fromtimestamp(self.timestamp / 1000, tz=pytz.utc)


class PayloadTooLargeException(APNSProgrammingException):
    """
    The message payload was too large.

    See Creating the Remote Notification Payload for details on maximum payload size.
    """


class TooManyProviderTokenUpdatesException(APNSServerException):
    """The provider token is being updated too often."""


class TooManyRequestsException(APNSServerException):
    """Too many requests were made consecutively to the same device token."""


class InternalServerErrorException(APNSServerException):
    """An internal server error occurred."""


class ServiceUnavailableException(APNSServerException):
    """The service is unavailable."""


class ShutdownException(APNSServerException):
    """The server is shutting down."""


def exception_class_for_reason(reason):
    return {
        'BadCollapseId': BadCollapseIdException,
        'BadDeviceToken': BadDeviceTokenException,
        'BadExpirationDate': BadExpirationDateException,
        'BadMessageId': BadMessageIdException,
        'BadPriority': BadPriorityException,
        'BadTopic': BadTopicException,
        'DeviceTokenNotForTopic': DeviceTokenNotForTopicException,
        'DuplicateHeaders': DuplicateHeadersException,
        'IdleTimeout': IdleTimeoutException,
        'MissingDeviceToken': MissingDeviceTokenException,
        'MissingTopic': MissingTopicException,
        'PayloadEmpty': PayloadEmptyException,
        'TopicDisallowed': TopicDisallowedException,
        'BadCertificate': BadCertificateException,
        'BadCertificateEnvironment': BadCertificateEnvironmentException,
        'ExpiredProviderToken': ExpiredProviderTokenException,
        'Forbidden': ForbiddenException,
        'InvalidProviderToken': InvalidProviderTokenException,
        'MissingProviderToken': MissingProviderTokenException,
        'BadPath': BadPathException,
        'MethodNotAllowed': MethodNotAllowedException,
        'Unregistered': UnregisteredException,
        'PayloadTooLarge': PayloadTooLargeException,
        'TooManyProviderTokenUpdates': TooManyProviderTokenUpdatesException,
        'TooManyRequests': TooManyRequestsException,
        'InternalServerError': InternalServerErrorException,
        'ServiceUnavailable': ServiceUnavailableException,
        'Shutdown': ShutdownException,
    }[reason]
