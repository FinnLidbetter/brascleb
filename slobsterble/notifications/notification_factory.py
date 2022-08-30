from slobsterble.notifications.apns_payload import Payload
from slobsterble.notifications.apns_client import Notification


class NotificationFactory:
    """Manager for creating notification requests."""

    @staticmethod
    def make_next_turn_notification(device_token, game_id, other_player_names, use_sandbox):
        """Create a Notification object for a next turn."""
        if len(other_player_names) == 1:
            other_players_string = other_player_names[0]
        elif len(other_player_names) == 2:
            other_players_string = f'{other_player_names[0]} and {other_player_names[1]}'
        else:
            other_players_string = f'{other_player_names[:-1].join(", ")}, and {other_player_names[-1]}'
        payload = Payload(
            alert=f'It is your turn to play against {other_players_string}!',
            badge=1,
            custom={'game_id': str(game_id)}
        )
        notification = Notification(payload=payload, token=device_token, use_sandbox=use_sandbox)
        return notification

    @staticmethod
    def make_new_game_notification(device_token, game_id, creator_name, your_turn, use_sandbox):
        payload = Payload(
            alert='%s started a new game.%s' % (
                creator_name, ' It is your turn to play!' if your_turn else ''),
            badge=1,
            custom={'game_id': str(game_id)}
        )
        notification = Notification(payload=payload, token=device_token, use_sandbox=use_sandbox)
        return notification
