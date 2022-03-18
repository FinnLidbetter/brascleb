from slobsterble.notifications.apns_payload import Payload
from slobsterble.notifications.apns_client import Notification


class NotificationFactory:
    """Manager for creating notification requests."""

    @staticmethod
    def make_next_turn_notification(device_token, game_id):
        """Create a Notification object for a next turn."""
        payload = Payload(
            alert='It is your turn to play!',
            badge=1,
            custom={'game_id': str(game_id)}
        )
        notification = Notification(payload=payload, token=device_token)
        return notification

    @staticmethod
    def make_new_game_notification(device_token, game_id, creator_name, your_turn):
        payload = Payload(
            alert='%s started a new game.%s' % (
                creator_name, ' It is your turn to play!' if your_turn else ''),
            badge=1,
            custom={'game_id': str(game_id)}
        )
        notification = Notification(payload=payload, token=device_token)
        return notification
