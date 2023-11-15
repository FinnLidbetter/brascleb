"""Setup the initial game state."""

import datetime
import random
from collections import defaultdict

import slobsterble.api_exceptions
from jsonschema import ValidationError
from jsonschema import validate as schema_validate
from slobsterble.app import db
from slobsterble.constants import (
    ACTIVE_GAME_LIMIT,
    GAME_PLAYERS_MAX,
    SPACES_TILES_RATIO_MIN,
    TILES_ON_RACK_MAX,
)
from slobsterble.models import Distribution, Game, GamePlayer, Player, TileCount
from slobsterble.utilities.tile_utilities import (
    build_tile_count_map,
    build_tile_object_map,
    fetch_all_tiles,
    fetch_mapped_tile_counts,
)
from sqlalchemy.orm import subqueryload

NEW_GAME_SCHEMA = {
    "type": "array",
    "minItems": 1,
    "maxItems": GAME_PLAYERS_MAX - 1,
    "uniqueItems": True,
    "items": {
        "type": "integer",
    },
}


class StatelessValidator:
    """Validate that the player ids given in the data are distinct integers."""

    def __init__(self, data):
        self.data = data
        self.validated = False

    def validate(self):
        """Perform all validation that is independent of the database state."""
        try:
            schema_validate(self.data, NEW_GAME_SCHEMA)
        except ValidationError:
            raise slobsterble.api_exceptions.NewGameSchemaException()
        self.validated = True
        return True


class StatefulValidator:
    """Validate that the players exist and are friends of the current user."""

    def __init__(self, data, player):
        self.data = data
        self.player = player
        self.validated = False

    def validate(self):
        """Perform all validation dependent on the database."""
        self._validate_friends()
        self.validated = True
        return True

    def _validate_no_self_opponent(self):
        """Validate that none of the opponents are the player themselves."""
        for friend_player_id in self.data:
            if friend_player_id == self.player.id:
                raise slobsterble.api_exceptions.NewGameSelfOpponentException()

    def _validate_friends(self):
        """Validate the given player ids correspond to friends of the user."""
        friend_id_set = {friend_player.id for friend_player in self.player.friends}
        for friend_player_id in self.data:
            if friend_player_id not in friend_id_set:
                raise slobsterble.api_exceptions.NewGameFriendException()

    def _validate_layout_distribution(self):
        """Validate that the player's tile distribution and layout are compatible."""
        num_tiles = sum(
            tile_count.count
            for tile_count in self.player.distribution.tile_distribution
        )
        rows = self.player.board_layout.rows
        columns = self.player.board_layout.columns
        if num_tiles * SPACES_TILES_RATIO_MIN > rows * columns:
            raise slobsterble.api_exceptions.NewGameLayoutDistributionException()

    def _validate_active_game_limit(self):
        """Validate that none of the players are in too many active games."""
        player_ids = [self.player.id] + self.data
        for player_id in player_ids:
            active_games = (
                db.session.query(GamePlayer)
                .filter_by(player_id=player_id)
                .join(GamePlayer.game)
                .filter(Game.completed is None)
                .count()
            )
            if active_games >= ACTIVE_GAME_LIMIT:
                player = db.session.query(Player).filter_by(player_id=player_id).one()
                raise slobsterble.api_exceptions.NewGameActiveGamesException(
                    "User %d has too many active games to start a new one."
                    % player.display_name
                )


class StateUpdater:
    """Create the Game and GamePlayers with initialized racks and bag."""

    def __init__(self, data, initiator):
        self.data = data
        self.initiator = initiator
        self.players = [self.initiator] + self._fetch_players()

    def update_state(self):
        """Create the Game and GamePlayer objects and commit to the database."""
        base_game = self._build_base_game()
        base_game_players = self._build_game_players(base_game)
        db.session.add(base_game)
        db.session.add_all(base_game_players)
        tile_objects = fetch_all_tiles(db.session)
        tile_object_map = build_tile_object_map(tile_objects)
        distribution_tile_counts = fetch_distribution_tile_counts(
            base_game.initial_distribution_id
        )
        bag_tile_count_map = build_tile_count_map(distribution_tile_counts)
        tiles_remaining = sum(bag_tile_count_map.values())
        for game_player in base_game_players:
            rack_tile_keys = random.sample(
                list(bag_tile_count_map.keys()),
                k=min(TILES_ON_RACK_MAX, tiles_remaining),
                counts=list(bag_tile_count_map.values()),
            )
            rack_tile_count_map = defaultdict(int)
            for tile_key in rack_tile_keys:
                rack_tile_count_map[tile_key] += 1
            mapped_rack_tile_counts = fetch_mapped_tile_counts(
                db.session, rack_tile_count_map, tile_object_map
            )
            rack_tile_counts = list(mapped_rack_tile_counts.values())
            game_player.rack = rack_tile_counts
            for tile_key, count in rack_tile_count_map.items():
                bag_tile_count_map[tile_key] -= count
                if bag_tile_count_map[tile_key] == 0:
                    del bag_tile_count_map[tile_key]
                tiles_remaining -= count
        mapped_bag_tile_counts = fetch_mapped_tile_counts(
            db.session, bag_tile_count_map, tile_object_map
        )
        base_game.bag_tiles = list(mapped_bag_tile_counts.values())
        db.session.commit()
        return base_game.id, base_game_players

    def _build_base_game(self):
        """Build the initial Game object without players or the bag state."""
        start_time = datetime.datetime.now()
        base_game = Game(
            dictionary_id=self.initiator.dictionary_id,
            board_layout_id=self.initiator.board_layout_id,
            initial_distribution_id=self.initiator.distribution_id,
            started=start_time,
            turn_number=0,
        )
        return base_game

    def _build_game_players(self, base_game):
        """Build the GamePlayer objects without rack states."""
        base_game_players = []
        shuffled_players = [player for player in self.players]
        random.shuffle(shuffled_players)
        for turn_order_val, player in enumerate(shuffled_players):
            base_game_players.append(
                GamePlayer(
                    player=player, score=0, turn_order=turn_order_val, game=base_game
                )
            )
        return base_game_players

    def _fetch_players(self):
        """Fetch the player objects for the player ids in the data."""
        players = []
        for player_id in self.data:
            players.append(db.session.query(Player).filter_by(id=player_id).one())
        return players


def fetch_distribution_tile_counts(distribution_id):
    """Get the tile count objects for the tile distribution."""
    distribution = (
        db.session.query(Distribution)
        .filter_by(id=distribution_id)
        .options(
            subqueryload(Distribution.tile_distribution).joinedload(TileCount.tile)
        )
        .one()
    )
    tile_counts = [tile_count for tile_count in distribution.tile_distribution]
    return tile_counts
