"""Setup pytest fixtures."""

import pytest
from flask_jwt_extended import create_access_token
from slobsterble.app import create_app
from slobsterble.app import db as database
from slobsterble.models import (
    BoardLayout,
    Dictionary,
    Distribution,
    Game,
    GamePlayer,
    Player,
    User,
)
from sqlalchemy.orm import scoped_session, sessionmaker


@pytest.fixture(scope="session", autouse=True)
def app_fixture():
    """Setup an app."""
    slobsterble_app = create_app()
    return slobsterble_app


@pytest.fixture
def client(app_fixture):
    """Setup the test client for making API calls."""
    with app_fixture.test_client() as test_client:
        yield test_client


@pytest.fixture(scope="session", autouse=True)
def _db(app_fixture):
    """Setup the database."""
    with app_fixture.app_context():
        yield database


@pytest.fixture(scope="function", autouse=True)
def db_session(_db):
    connection = _db.engine.connect()
    transaction = connection.begin_nested()
    _db.session = scoped_session(session_factory=sessionmaker(bind=connection))
    yield _db.session
    transaction.rollback()
    connection.close()
    _db.session.remove()


def _build_user(name):
    """Build a User object."""
    user = User(username=name)
    user.set_password(name)
    return user


def _build_player(user, session):
    """Build a Player object."""
    default_dictionary = session.query(Dictionary).filter_by(id=1).first()
    default_board_layout = session.query(BoardLayout).filter_by(id=1).first()
    default_distribution = session.query(Distribution).filter_by(id=1).first()
    player = Player(
        user=user,
        display_name=user.username,
        dictionary=default_dictionary,
        board_layout=default_board_layout,
        distribution=default_distribution,
    )
    return player


@pytest.fixture
def alice(db_session):
    """Create a User and Player called Alice."""
    user = _build_user("Alice")
    player = _build_player(user, db_session)
    db_session.add(user)
    db_session.add(player)
    db_session.commit()
    yield user, player
    db_session.delete(player)
    db_session.delete(user)
    db_session.commit()


@pytest.fixture
def bob(db_session):
    """Create a User and Player called Bob."""
    user = _build_user("Bob")
    player = _build_player(user, db_session)
    db_session.add(user)
    db_session.add(player)
    db_session.commit()
    yield user, player
    db_session.delete(player)
    db_session.delete(user)
    db_session.commit()


@pytest.fixture
def carol(db_session):
    """Create a User and Player called Carol."""
    user = _build_user("Carol")
    player = _build_player(user, db_session)
    db_session.add(user)
    db_session.add(player)
    db_session.commit()
    yield user, player
    db_session.delete(player)
    db_session.delete(user)
    db_session.commit()


@pytest.fixture
def alice_bob_mutual_friends(db_session, alice, bob):
    """Make Alice and Bob mutual friends."""
    _, alice_player = alice
    _, bob_player = bob
    initial_alice_friends = alice_player.friends.copy()
    initial_bob_friends = bob_player.friends.copy()
    alice_player.friends.append(bob_player)
    bob_player.friends.append(alice_player)
    db_session.add(alice_player)
    db_session.add(bob_player)
    db_session.commit()
    yield alice_player, bob_player
    alice_player.friends = initial_alice_friends
    bob_player.friends = initial_bob_friends
    db_session.add(alice_player)
    db_session.add(bob_player)
    db_session.commit()


@pytest.fixture
def alice_carol_friend(db_session, alice, carol):
    """Make Carol a friend of Alice, but not the converse."""
    _, alice_player = alice
    _, carol_player = carol
    initial_alice_friends = alice_player.friends.copy()
    alice_player.friends.append(carol_player)
    db_session.add(alice_player)
    db_session.commit()
    yield alice_player, carol_player
    alice_player.friends = initial_alice_friends
    db_session.add(alice_player)
    db_session.commit()


@pytest.fixture
def alice_headers(alice):
    """Get access token headers for Alice."""
    alice_user, _ = alice
    access_token = create_access_token(alice_user)
    headers = {"Authorization": "Bearer {}".format(access_token)}
    return headers


@pytest.fixture
def bob_headers(bob):
    """Get access token headers for Bob."""
    bob_user, _ = bob
    access_token = create_access_token(bob_user)
    headers = {"Authorization": "Bearer {}".format(access_token)}
    return headers


@pytest.fixture
def carol_headers(carol):
    """Get access token headers for Carol."""
    carol_user, _ = carol
    access_token = create_access_token(carol_user)
    headers = {"Authorization": "Bearer {}".format(access_token)}
    return headers


@pytest.fixture
def alice_bob_game(alice, bob, db_session):
    """Setup a Game between Alice and Bob."""
    _, alice_player = alice
    _, bob_player = bob
    game = Game(dictionary_id=1, board_layout_id=1, initial_distribution_id=1)
    alice_game_player = GamePlayer(player=alice_player, game=game, turn_order=0)
    bob_game_player = GamePlayer(player=bob_player, game=game, turn_order=1)
    game.game_player_to_play = alice_game_player
    db_session.add(game)
    db_session.add(alice_game_player)
    db_session.add(bob_game_player)
    db_session.commit()
    yield game, alice_game_player, bob_game_player
    db_session.delete(bob_game_player)
    db_session.delete(alice_game_player)
    db_session.delete(game)
    db_session.commit()


@pytest.fixture
def alice_bob_carol_game(alice, bob, carol, db_session):
    """Setup a Game between Alice, Bob, and Carol."""
    _, alice_player = alice
    _, bob_player = bob
    _, carol_player = carol
    game = Game(dictionary_id=1, board_layout_id=1, initial_distribution_id=1)
    alice_game_player = GamePlayer(player=alice_player, game=game, turn_order=0)
    bob_game_player = GamePlayer(player=bob_player, game=game, turn_order=1)
    carol_game_player = GamePlayer(player=carol_player, game=game, turn_order=2)
    game.game_player_to_play = alice_game_player
    db_session.add(game)
    db_session.add(alice_game_player)
    db_session.add(bob_game_player)
    db_session.add(carol_game_player)
    db_session.commit()
    yield game, alice_game_player, bob_game_player, carol_game_player
    db_session.delete(carol_game_player)
    db_session.delete(bob_game_player)
    db_session.delete(alice_game_player)
    db_session.delete(game)
    db_session.commit()
