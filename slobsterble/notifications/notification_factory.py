from apns2.payload import Payload
from apns2.client import Notification


class NotificationFactory:
    """Manager for creating notification requests."""

    @staticmethod
    def make_next_turn_notification(device_token, game_id):
        """Create a Notification object for a next turn."""
        payload = Payload(
            alert='It is your turn to play next!',
            badge=1,
            custom={'game_id': str(game_id)}
        )
        notification = Notification(payload=payload, token=device_token)
        return notification

