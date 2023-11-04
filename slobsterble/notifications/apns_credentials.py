import time

import jwt


DEFAULT_TOKEN_LIFETIME = 2700
DEFAULT_TOKEN_ENCRYPTION_ALGORITHM = "ES256"
PROTOCOL = "https"


class TokenCredentials:
    """JWT token based authentication."""

    def __init__(
        self,
        auth_key_path: str,
        auth_key_id: str,
        team_id: str,
        encryption_algorithm: str = DEFAULT_TOKEN_ENCRYPTION_ALGORITHM,
        token_lifetime: int = DEFAULT_TOKEN_LIFETIME,
    ) -> None:
        self.__auth_key = self._get_signing_key(auth_key_path)
        self.__auth_key_id = auth_key_id
        self.__team_id = team_id
        self.__encryption_algorithm = encryption_algorithm
        self.__token_lifetime = token_lifetime
        self.__jwt_token = None

    def get_authorization_header(self) -> str:
        token = self._get_or_create_topic_token()
        return "bearer %s" % token

    def _is_expired_token(self, issue_date: float) -> bool:
        return time.time() > issue_date + self.__token_lifetime

    @staticmethod
    def _get_signing_key(key_path: str) -> str:
        secret = ""
        if key_path:
            with open(key_path) as f:
                secret = f.read()
        return secret

    def _get_or_create_topic_token(self) -> str:
        # dict of topic to issue date and JWT token
        token_pair = self.__jwt_token
        if token_pair is None or self._is_expired_token(token_pair[0]):
            # Create a new token
            issued_at = time.time()
            token_dict = {
                "iss": self.__team_id,
                "iat": issued_at,
            }
            headers = {
                "alg": self.__encryption_algorithm,
                "kid": self.__auth_key_id,
            }
            jwt_token = jwt.encode(
                token_dict,
                self.__auth_key,
                algorithm=self.__encryption_algorithm,
                headers=headers,
            )

            # Cache JWT token for later use. One JWT token per connection.
            # https://developer.apple.com/documentation/usernotifications/setting_up_a_remote_notification_server/establishing_a_token-based_connection_to_apns
            self.__jwt_token = (issued_at, jwt_token)
            return jwt_token
        else:
            return token_pair[1]
