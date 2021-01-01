"""Setup the initial game state."""
from collections import defaultdict
import random

from sqlalchemy.orm import joinedload, subqueryload

from slobsterble import db
from slobsterble.constants import DISTRIBUTION, TILE_VALUES, TILES_ON_RACK_MAX
from slobsterble.models import Game, GamePlayer, Tile, TileCount


def initialize_bag(game_id):
    """Initialize the game's bag with the initial tile distribution."""
    tile_counts = db.session.query(TileCount).options(
        joinedload(TileCount.tile)).all()
    tile_count_dict = {(tile_count.tile.letter, tile_count.tile.value,
                        tile_count.count): tile_count
                       for tile_count in tile_counts}
    game = db.session.query(Game).filter(Game.id == game_id).options(
        subqueryload(Game.bag_tiles)).first()
    for letter in DISTRIBUTION.keys():
        value = TILE_VALUES[letter]
        count = DISTRIBUTION[letter]
        game.bag_tiles.append(tile_count_dict[(letter, value, count)])
    db.session.commit()


def initialize_racks(game_id):
    """Initialize the players' racks with tiles."""
    game = db.session.query(Game).filter(Game.id == game_id).options(
        subqueryload(Game.bag_tiles)).options(
        subqueryload(Game.game_players).subqueryload(GamePlayer.rack)).first()
    tile_counts = db.session.query(TileCount).options(
        joinedload(TileCount.tile)).all()
    tile_count_dict = {(tile_count.tile_id, tile_count.count): tile_count
                       for tile_count in tile_counts}
    bag_tiles_with_repeats = []
    bag_tile_counts = defaultdict(int)
    for tile_count in game.bag_tiles:
        for _ in range(tile_count.count):
            bag_tiles_with_repeats.append(tile_count.tile_id)
            bag_tile_counts[tile_count.tile_id] += 1
    num_tiles_to_draw = TILES_ON_RACK_MAX * len(game.game_players)
    tile_ids = random.sample(bag_tiles_with_repeats, k=num_tiles_to_draw)
    for player_index, game_player in enumerate(game.game_players):
        rack = defaultdict(int)
        for rack_index in range(TILES_ON_RACK_MAX):
            drawn_tile_index = player_index * TILES_ON_RACK_MAX + rack_index
            tile_id = tile_ids[drawn_tile_index]
            rack[tile_id] += 1
            bag_tile_counts[tile_id] -= 1
            if bag_tile_counts[tile_id] == 0:
                del bag_tile_counts[tile_id]
        for tile_id, count in rack.items():
            game_player.rack.append(tile_count_dict[(tile_id, count)])
    bag_tiles = [
        tile_count_dict[(tile_id, count)] for tile_id, count in bag_tile_counts.items()]
    game.bag_tiles = bag_tiles
    db.session.commit()
