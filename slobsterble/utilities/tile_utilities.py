"""Common functions for querying and managing Tile and TileCount objects."""

from collections import defaultdict

from slobsterble.models import Tile, TileCount
from slobsterble.utilities.db_utilities import fetch_or_create


def build_tile_object_map(tiles):
    """Index Tile objects by tuples of their attributes."""
    tile_object_map = {}
    for tile in tiles:
        tile_key = (tile.letter, tile.value, tile.is_blank)
        tile_object_map[tile_key] = tile
    return tile_object_map


def build_tile_count_map(tile_counts):
    """Build a map from a tile key to a count."""
    tile_count_map = defaultdict(int)
    for tile_count in tile_counts:
        tile = tile_count.tile
        tile_key = (tile.letter, tile.value, tile.is_blank)
        tile_count_map[tile_key] = tile_count.count
    return tile_count_map


def fetch_mapped_tile_counts(session, tile_counts_map, tile_object_map):
    """
    Fetch tile count objects.

    If the required TileCount or Tile objects do not exist, then those objects
    will be created and committed to the database.
    """
    tile_counts_object_map = {}
    for tile_key, count in tile_counts_map.items():
        if tile_key not in tile_object_map:
            tile_object_map[tile_key] = fetch_or_create(
                session, Tile,
                letter=tile_key[0], value=tile_key[1], is_blank=tile_key[2])[0]
        tile_counts_object_map[(tile_key, count)] = fetch_or_create(
            session, TileCount,
            tile_id=tile_object_map[tile_key].id, count=count)[0]
    return tile_counts_object_map


def fetch_all_tiles(session):
    """Fetch all tiles."""
    return session.query(Tile).all()

