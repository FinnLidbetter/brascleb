"""Test the play turn API."""

from slobsterble.play_exceptions import (
    PlayCurrentTurnException,
    PlaySchemaException,
    PlayAxisException,
)


def test_game_does_not_exist(client, alice_headers):
    """Test submitting a play to a game that does not exist."""
    resp = client.post('/game/1', json=[], headers=alice_headers)
    assert resp.status_code == 400
    assert resp.get_data(as_text=True) == 'Game does not exist.'


def test_game_no_authorization(client):
    """Test submitting a play without a JWT."""
    resp = client.post('/game/1', json=[])
    assert resp.status_code == 401
    assert "Missing JWT in headers or cookies" in resp.get_data(as_text=True)


def test_forbidden_user(client, bob_headers, carol_headers, alice_bob_game):
    """Test not the user's turn or user is not a player in the game."""
    game, _, __ = alice_bob_game
    resp = client.post(f'/game/{game.id}', json=[], headers=carol_headers)
    assert resp.status_code == 403
    assert resp.get_data(as_text=True) == PlayCurrentTurnException.default_message
    resp = client.post(f'/game/{game.id}', json=[], headers=bob_headers)
    assert resp.status_code == 403
    assert resp.get_data(as_text=True) == PlayCurrentTurnException.default_message


def test_bad_schema(client, alice_headers, alice_bob_game):
    """A blank without a defined letter cannot be played."""
    game, _, __ = alice_bob_game
    letterless_blank_play = [
        {'letter': None, 'is_blank': True, 'is_exchange': False,
         'row': 7, 'column': 7, 'value': 0}]
    lettered_blank_exchange = [
        {'letter': 'A', 'is_blank': True, 'is_exchange': True,
         'row': None, 'column': None, 'value': 0}]
    play_exchange_mix = [
        {'letter': 'A', 'is_blank': False, 'is_exchange': False,
         'row': 7, 'column': 7, 'value': 1},
        {'letter': 'A', 'is_blank': False, 'is_exchange': True,
         'row': None, 'column': None, 'value': 1}]
    row_exchange = [
        {'letter': 'B', 'is_blank': False, 'is_exchange': True, 'value': 3,
         'row': 7, 'column': None}]
    column_exchange = [
        {'letter': 'B', 'is_blank': False, 'is_exchange': True, 'value': 3,
         'row': None, 'column': 7}]
    plays = [
        letterless_blank_play, lettered_blank_exchange, play_exchange_mix,
        row_exchange, column_exchange
    ]
    for bad_play in plays:
        resp = client.post(
            f'/game/{game.id}', json=bad_play, headers=alice_headers)
        assert resp.status_code == 400
        assert resp.get_data(as_text=True) == PlaySchemaException.default_message

def test_pass(client, alice_headers, alice_bob_game):
    """Test playing a turn by submitting no data."""
    game, _, __ = alice_bob_game
    resp = client.post(f'/game/{game.id}', json=[], headers=alice_headers)
    assert resp.status_code == 200
    assert resp.get_data(as_text=True) == 'Turn played successfully.'
