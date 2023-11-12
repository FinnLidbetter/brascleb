"""Test the new game API and controller."""

import json
from collections import defaultdict

import pytest
from slobsterble.api_exceptions import NewGameFriendException, NewGameSchemaException
from slobsterble.constants import TILES_ON_RACK_MAX
from slobsterble.game_setup_controller import (
    StatefulValidator,
    StatelessValidator,
    StateUpdater,
)
from slobsterble.models import Game, GamePlayer, TileCount
from sqlalchemy.orm import subqueryload


def test_game_no_authorization(client):
    """Test trying to start a new game without a JWT."""
    resp = client.get("/api/new-game")
    assert resp.status_code == 401
    assert "Missing Authorization Header" in resp.get_data(as_text=True)
    resp = client.post("/api/new-game", json=[2])
    assert resp.status_code == 401
    assert "Missing Authorization Header" in resp.get_data(as_text=True)


def test_stateless_validation():
    """Tests for plausible data, independent of database state."""
    cases = [
        ([], False),  # Empty array is not valid.
        ([1], True),  # Valid single opponent.
        ([1, 1], False),  # Duplicate values are not valid.
        ([1, 2, 3], True),  # Valid multiple opponents.
        ([1, 2, 3, 4], False),  # Too many opponents.
        (["1"], False),  # Bad data type.
    ]
    for data, expected_valid in cases:
        stateless_validator = StatelessValidator(data)
        if not expected_valid:
            with pytest.raises(NewGameSchemaException):
                stateless_validator.validate()
        else:
            assert stateless_validator.validate()


def test_not_friends(alice, bob):
    """Test trying to create a game with someone that is not a friend."""
    _, alice_player = alice
    _, bob_player = bob
    stateful_validator = StatefulValidator([bob_player.id], alice_player)
    with pytest.raises(NewGameFriendException):
        stateful_validator.validate()
    stateful_validator = StatefulValidator([alice_player.id], bob_player)
    with pytest.raises(NewGameFriendException):
        stateful_validator.validate()


def test_valid_friends(alice_bob_mutual_friends, alice_carol_friend):
    """Test creating games with friends."""
    alice_player, bob_player = alice_bob_mutual_friends
    alice_player, carol_player = alice_carol_friend
    stateful_validator = StatefulValidator(
        [bob_player.id, carol_player.id], alice_player
    )
    assert stateful_validator.validate()
    # Carol is not a friend of Bob, so Bob cannot start the game.
    stateful_validator = StatefulValidator(
        [alice_player.id, carol_player.id], bob_player
    )
    with pytest.raises(NewGameFriendException):
        stateful_validator.validate()


def test_update_state(db_session, alice_bob_mutual_friends):
    """Test creating a game."""
    alice_player, bob_player = alice_bob_mutual_friends
    state_updater = StateUpdater([bob_player.id], alice_player)
    state_updater.update_state()
    created_game = (
        db_session.query(Game)
        .options(
            subqueryload(Game.game_players)
            .subqueryload(GamePlayer.rack)
            .joinedload(TileCount.tile),
            subqueryload(Game.bag_tiles).joinedload(TileCount.tile),
        )
        .order_by(Game.created.desc())
        .first()
    )
    assert len(created_game.game_players) == 2
    assert created_game.initial_distribution_id == alice_player.distribution_id
    assert created_game.board_layout_id == alice_player.board_layout_id
    assert created_game.dictionary_id == alice_player.dictionary_id
    assert created_game.turn_number == 0
    distribution_tiles = defaultdict(int)
    for tile_count in alice_player.distribution.tile_distribution:
        distribution_tiles[tile_count.tile_id] += tile_count.count
    bag_and_rack_tiles = defaultdict(int)
    for tile_count in created_game.bag_tiles:
        bag_and_rack_tiles[tile_count.tile_id] += tile_count.count
    for game_player in created_game.game_players:
        num_player_tiles = 0
        for tile_count in game_player.rack:
            bag_and_rack_tiles[tile_count.tile_id] += tile_count.count
            num_player_tiles += tile_count.count
        assert num_player_tiles == TILES_ON_RACK_MAX
    assert distribution_tiles == bag_and_rack_tiles
    turn_order_numbers = {
        game_player.turn_order for game_player in created_game.game_players
    }
    assert turn_order_numbers == {0, 1}


def test_valid_gets(
    client,
    alice_bob_mutual_friends,
    alice_carol_friend,
    alice_headers,
    bob_headers,
    carol_headers,
):
    """Test getting data for starting a new game."""
    _, bob_player = alice_bob_mutual_friends
    alice_player, carol_player = alice_carol_friend
    alice_resp = client.get("/api/new-game", headers=alice_headers)
    alice_data = json.loads(alice_resp.get_data(as_text=True))
    alice_data["friends"].sort(key=lambda dct: dct["display_name"])
    assert alice_data == {
        "friends": [
            {"display_name": bob_player.display_name, "player_id": bob_player.id},
            {"display_name": carol_player.display_name, "player_id": carol_player.id},
        ]
    }
    bob_resp = client.get("/api/new-game", headers=bob_headers)
    bob_data = json.loads(bob_resp.get_data(as_text=True))
    assert bob_data == {
        "friends": [
            {"display_name": alice_player.display_name, "player_id": alice_player.id}
        ]
    }
    carol_resp = client.get("/api/new-game", headers=carol_headers)
    carol_data = json.loads(carol_resp.get_data(as_text=True))
    assert carol_data == {"friends": []}


def test_valid_post(client, db_session, alice_bob_mutual_friends, alice_headers):
    """Test submitting a valid POST to the New Game API."""
    alice_player, bob_player = alice_bob_mutual_friends
    resp = client.post("/api/new-game", json=[bob_player.id], headers=alice_headers)
    assert resp.status_code == 200
    assert resp.get_data(as_text=True) == "1"


def test_invalid_post(client, bob, alice_headers):
    """Test submitting an invalid POST to the New Game API."""
    _, bob_player = bob
    resp = client.post("/api/new-game", json=[bob_player.id], headers=alice_headers)
    assert resp.status_code == 400
    assert resp.get_data(as_text=True) == NewGameFriendException.default_message
