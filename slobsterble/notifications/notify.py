"""Module for processing notifications."""

from slobsterble.app import apns, db
from slobsterble.models import Device, Game, GamePlayer
from slobsterble.notifications.notification_factory import NotificationFactory


def notify_next_player(game_id):
    """Notify the next player in the game that it is their turn."""
    game_players_query = db.session.query(Game).filter(
        Game.id == game_id).join(Game.game_players).join(GamePlayer.player).one()
    num_players = len(game_players_query.game_players)
    next_game_player = None
    for game_player in game_players_query.game_players:
        if game_players_query.turn_number % num_players == game_player.turn_order:
            next_game_player = game_player
            break
    player_devices = db.session.query(Device).filter(
        Device.user_id == next_game_player.player.user_id).all()
    notification_requests = []
    for player_device in player_devices:
        notification_requests.append(
            NotificationFactory.make_next_turn_notification(player_device.device_token, game_id))
    apns.notify(notification_requests)


def notify_new_game(game_id, game_players, creator_player):
    notification_requests = []
    for game_player in game_players:
        if game_player.player_id == creator_player.id:
            # Do not notify the player that created the game.
            continue
        player_devices = db.session.query(Device).filter(
            Device.user_id == game_player.player.user_id).all()
        for player_device in player_devices:
            notification_requests.append(
                NotificationFactory.make_new_game_notification(
                    device_token=player_device.device_token,
                    game_id=game_id,
                    creator_name=creator_player.display_name,
                    your_turn=game_player.turn_order == 0
                )
            )
        apns.notify(notification_requests)
