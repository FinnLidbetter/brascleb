"""Test the play turn API."""

from unittest.mock import patch

import pytest

from slobsterble.game_play_controller import (
    StatelessValidator,
    StatefulValidator,
    fetch_game_state,
)
from slobsterble.api_exceptions import (
    PlayCurrentTurnException,
    PlaySchemaException,
)
from slobsterble.models import Game, GamePlayer


def test_game_does_not_exist(client, alice_headers):
    """Test submitting a play to a game that does not exist."""
    game_id = 1
    resp = client.post(f'/game/{game_id}', json=[], headers=alice_headers)
    assert resp.status_code == 400
    assert resp.get_data(as_text=True) == 'Game does not exist.'


def test_game_no_authorization(client):
    """Test submitting a play without a JWT."""
    resp = client.post('/game/1', json=[])
    assert resp.status_code == 401
    assert "Missing JWT in headers or cookies" in resp.get_data(as_text=True)


def test_forbidden_user(alice_bob_game, alice, bob, carol):
    """Test not the user's turn or user is not a player in the game."""
    game, alice_game_player, _ = alice_bob_game
    bob_user, _ = bob
    carol_user, _ = carol
    game_state = fetch_game_state(game.id)
    with patch('slobsterble.game_play_controller.current_user', bob_user):
        stateful_validator = StatefulValidator([], game_state, alice_game_player)
        with pytest.raises(PlayCurrentTurnException):
            stateful_validator.validate()
        assert not stateful_validator.validated
    with patch('slobsterble.game_play_controller.current_user', carol_user):
        stateful_validator = StatefulValidator([], game_state, alice_game_player)
        with pytest.raises(PlayCurrentTurnException):
            stateful_validator.validate()
        assert not stateful_validator.validated
    # Verify that the testing approach is good.
    alice_user, _ = alice
    with patch('slobsterble.game_play_controller.current_user', alice_user):
        stateful_validator = StatefulValidator([], game_state, alice_game_player)
        assert stateful_validator.validate()
        assert stateful_validator.validated


def test_bad_schema(alice_bob_game):
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
        stateless_validator = StatelessValidator(bad_play)
        with pytest.raises(PlaySchemaException):
            stateless_validator.validate()
        assert not stateless_validator.validated


def test_pass(db, client, alice_headers, alice_bob_game):
    """Test playing a turn by submitting no data."""
    game, alice_game_player, __ = alice_bob_game
    assert game.turn_number == 0
    assert alice_game_player.score == 0
    resp = client.post(f'/game/{game.id}', json=[], headers=alice_headers)
    assert resp.status_code == 200
    assert resp.get_data(as_text=True) == 'Turn played successfully.'
    game = db.session.query(Game).filter_by(id=game.id).one()
    alice_game_player = db.session.query(GamePlayer).filter_by(
        id=alice_game_player.id).one()
    # Turn number increases.
    assert game.turn_number == 1
    assert alice_game_player.score == 0
