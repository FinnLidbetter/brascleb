"""Test the move history API."""

import datetime
import json

import slobsterble.models


def test_game_does_not_exist(client, alice_headers):
    """Test game not found returns 400."""
    resp = client.get("/api/game/1/move-history", headers=alice_headers)
    assert resp.status_code == 400
    assert resp.get_data(as_text=True) == "No game with ID 1."


def test_unauthorized_user(client, carol_headers, alice_bob_game):
    """A user that is not a player in the game cannot see the move history."""
    game, _, __ = alice_bob_game
    resp = client.get(f"/api/game/{game.id}/move-history", headers=carol_headers)
    assert resp.status_code == 401
    assert resp.get_data(as_text=True) == "User is not authorized."


def test_no_authorization(client, alice_bob_game):
    """The API returns no result if there is no authorization."""
    game, _, __ = alice_bob_game
    resp = client.get(f"/api/game/{game.id}/move-history")
    assert resp.status_code == 401
    assert "Missing Authorization Header" in resp.get_data(as_text=True)


def test_no_moves(client, alice_headers, alice_bob_game):
    """Test getting the move history when there have been no moves yet."""
    game, _, __ = alice_bob_game
    resp = client.get(f"/api/game/{game.id}/move-history", headers=alice_headers)
    assert resp.status_code == 200
    data = json.loads(resp.get_data())
    assert len(data) == 2
    for player_moves in data:
        assert player_moves["moves"] == []


def test_one_regular_move(
    client, alice_headers, bob_headers, alice_bob_game, db_session
):
    """Test fetching move history from a game with one word move played."""
    game, alice_game_player, bob_game_player = alice_bob_game
    move = slobsterble.models.Move(
        game_player=alice_game_player,
        primary_word="abc",
        secondary_words="bob,cat",
        turn_number=0,
        score=15,
        played_time=datetime.datetime.now(),
    )
    db_session.add(move)
    db_session.commit()
    # Results are the same for both players.
    for headers in alice_headers, bob_headers:
        resp = client.get(f"/api/game/{game.id}/move-history", headers=headers)
        data = json.loads(resp.get_data())
        assert resp.status_code == 200
        assert len(data) == 2
        alice_player_moves = data[0]
        bob_player_moves = data[1]
        assert alice_player_moves["turn_order"] == 0
        assert bob_player_moves["turn_order"] == 1
        assert len(bob_player_moves["moves"]) == 0
        assert "id" in alice_player_moves["player"]
        assert "id" in bob_player_moves["player"]
        moves = alice_player_moves["moves"]
        assert moves == [
            {
                "primary_word": "abc",
                "secondary_words": "bob,cat",
                "exchanged_tiles": [],
                "score": 15,
                "turn_number": 0,
            }
        ]


def test_exchange(client, alice_headers, alice_bob_game, db_session):
    """Test that a move where tiles were exchanged serializes correctly."""
    game, alice_game_player, bob_game_player = alice_bob_game
    a_3 = (
        db_session.query(slobsterble.models.TileCount)
        .filter_by(count=3)
        .join(slobsterble.models.TileCount.tile)
        .filter_by(letter="a", is_blank=False)
        .first()
    )
    blank_1 = (
        db_session.query(slobsterble.models.TileCount)
        .filter_by(count=1)
        .join(slobsterble.models.TileCount.tile)
        .filter_by(letter=None, is_blank=True)
        .first()
    )
    z_1 = (
        db_session.query(slobsterble.models.TileCount)
        .filter_by(count=1)
        .join(slobsterble.models.TileCount.tile)
        .filter_by(letter="z", is_blank=False)
        .first()
    )
    c_2 = (
        db_session.query(slobsterble.models.TileCount)
        .filter_by(count=2)
        .join(slobsterble.models.TileCount.tile)
        .filter_by(letter="c", is_blank=False)
        .first()
    )
    exchanged_tiles = [a_3, blank_1, z_1, c_2]
    move = slobsterble.models.Move(
        game_player=alice_game_player,
        primary_word=None,
        secondary_words=None,
        turn_number=0,
        score=0,
        exchanged_tiles=exchanged_tiles,
        played_time=datetime.datetime.now(),
    )
    db_session.add(move)
    db_session.commit()
    resp = client.get(f"/api/game/{game.id}/move-history", headers=alice_headers)
    data = json.loads(resp.get_data())
    assert resp.status_code == 200
    assert len(data) == 2
    alice_player_moves = data[0]
    moves = alice_player_moves["moves"]
    assert len(moves) == 1
    assert moves[0]["primary_word"] is None
    assert moves[0]["secondary_words"] is None
    assert moves[0]["score"] == 0
    assert moves[0]["turn_number"] == 0
    # Exchanged tiles have the expected values and appear in the expected order.
    expected_exchanged = [
        {
            "tile": {
                "letter": a_3.tile.letter,
                "is_blank": False,
                "value": a_3.tile.value,
            },
            "count": 3,
        },
        {
            "tile": {
                "letter": c_2.tile.letter,
                "is_blank": False,
                "value": c_2.tile.value,
            },
            "count": 2,
        },
        {
            "tile": {
                "letter": z_1.tile.letter,
                "is_blank": False,
                "value": z_1.tile.value,
            },
            "count": 1,
        },
        {
            "tile": {
                "letter": None,
                "is_blank": True,
                "value": blank_1.tile.value,
            },
            "count": 1,
        },
    ]
    assert moves[0]["exchanged_tiles"] == expected_exchanged


def test_pass_move(client, alice_headers, alice_bob_game, db_session):
    """Test getting move history including a passed turn."""
    game, alice_game_player, bob_game_player = alice_bob_game
    move = slobsterble.models.Move(
        game_player=alice_game_player,
        primary_word=None,
        secondary_words=None,
        turn_number=0,
        score=0,
        exchanged_tiles=[],
        played_tiles=[],
        played_time=datetime.datetime.now(),
    )
    db_session.add(move)
    db_session.commit()
    resp = client.get(f"/api/game/{game.id}/move-history", headers=alice_headers)
    data = json.loads(resp.get_data())
    assert resp.status_code == 200
    assert len(data) == 2
    alice_player_moves = data[0]
    moves = alice_player_moves["moves"]
    assert moves == [
        {
            "primary_word": None,
            "secondary_words": None,
            "exchanged_tiles": [],
            "score": 0,
            "turn_number": 0,
        }
    ]


def test_three_player_game(
    client, alice_headers, bob_headers, carol_headers, alice_bob_carol_game, db_session
):
    """Test getting history for multiple moves in a three player game."""
    game, alice_game_player, bob_game_player, carol_game_player = alice_bob_carol_game
    now = datetime.datetime.now()
    # Alice passes on move 0.
    move_0 = slobsterble.models.Move(
        game_player=alice_game_player,
        turn_number=0,
        score=0,
        primary_word=None,
        secondary_words=None,
        played_time=now,
    )
    # Bob plays 'bravo' on move 1.
    move_1 = slobsterble.models.Move(
        game_player=bob_game_player,
        turn_number=1,
        score=26,
        primary_word="bravo",
        secondary_words=None,
        played_time=now,
    )
    z_1 = (
        db_session.query(slobsterble.models.TileCount)
        .filter_by(count=1)
        .join(slobsterble.models.TileCount.tile)
        .filter_by(letter="Z", is_blank=False)
        .first()
    )
    # Carol exchanges 1 tile on move 2.
    move_2 = slobsterble.models.Move(
        game_player=carol_game_player,
        turn_number=2,
        score=0,
        primary_word=None,
        secondary_words=None,
        played_time=now,
        exchanged_tiles=[z_1],
    )
    # Alice plays 'golf' and 'go' on move 3.
    move_3 = slobsterble.models.Move(
        game_player=alice_game_player,
        turn_number=3,
        score=12,
        primary_word="golf",
        secondary_words="go",
        played_time=now,
    )
    for move in [move_0, move_1, move_2, move_3]:
        db_session.add(move)
    db_session.commit()
    expected_alice_moves = [
        {
            "primary_word": None,
            "secondary_words": None,
            "exchanged_tiles": [],
            "score": 0,
            "turn_number": 0,
        },
        {
            "primary_word": "golf",
            "secondary_words": "go",
            "exchanged_tiles": [],
            "score": 12,
            "turn_number": 3,
        },
    ]
    expected_bob_moves = [
        {
            "primary_word": "bravo",
            "secondary_words": None,
            "exchanged_tiles": [],
            "score": 26,
            "turn_number": 1,
        },
    ]
    expected_carol_moves = [
        {
            "primary_word": None,
            "secondary_words": None,
            "exchanged_tiles": [
                {
                    "tile": {
                        "letter": z_1.tile.letter,
                        "is_blank": False,
                        "value": z_1.tile.value,
                    },
                    "count": 1,
                }
            ],
            "score": 0,
            "turn_number": 2,
        }
    ]
    for headers in alice_headers, bob_headers, carol_headers:
        resp = client.get(f"/api/game/{game.id}/move-history", headers=headers)
        data = json.loads(resp.get_data())
        assert resp.status_code == 200
        assert len(data) == 3
        alice_moves = data[0]["moves"]
        bob_moves = data[1]["moves"]
        carol_moves = data[2]["moves"]
        assert alice_moves == expected_alice_moves
        assert bob_moves == expected_bob_moves
        assert carol_moves == expected_carol_moves
