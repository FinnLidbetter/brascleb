"""Test the move history API."""

import datetime
import json

import slobsterble.models


def test_game_does_not_exist(alice_client):
    """Test game not found returns 400."""
    resp = alice_client.get('/api/game/1/move-history')
    assert resp.status_code == 400
    assert resp.get_data(as_text=True) == 'No game with ID 1.'


def test_unauthorized_user(carol_client, alice_bob_game):
    """A user that is not a player in the game cannot see the move history."""
    game, _, __ = alice_bob_game
    resp = carol_client.get('/api/game/%s/move-history' % str(game.id))
    assert resp.status_code == 401
    assert resp.get_data(as_text=True) == 'User is not authorized.'


def test_no_moves(alice_client, alice_bob_game):
    """Test getting the move history when there have been no moves yet."""
    game, _, __ = alice_bob_game
    resp = alice_client.get('/api/game/%s/move-history' % str(game.id))
    assert resp.status_code == 200
    data = json.loads(resp.get_data())
    assert len(data['game_players']) == 2
    for player_moves in data['game_players']:
        assert player_moves['moves'] == []


def test_one_regular_move(alice_client, alice_bob_game, db):
    """"""
    game, alice_game_player, bob_game_player = alice_bob_game
    move = slobsterble.models.Move(
        game_player=alice_game_player,
        primary_word='abc', secondary_words='bob,cat',
        turn_number=0, score=15,
        played_time=datetime.datetime.now())
    db.session.add(move)
    db.session.commit()
    resp = alice_client.get('/api/game/%s/move-history' % str(game.id))
    data = json.loads(resp.get_data())
    assert resp.status_code == 200
    assert len(data['game_players']) == 2
    alice_player_moves = data['game_players'][0]
    if alice_player_moves['player']['display_name'] != 'Alice':
        alice_player_moves = data['game_players'][1]
    moves = alice_player_moves['moves']
    assert moves == [
        {'primary_word': 'abc', 'secondary_words': 'bob,cat',
         'tiles_exchanged': [], 'score': 15, 'turn_number': 0}]
    db.session.delete(move)
    db.session.commit()
