import datetime
from collections import defaultdict, deque, namedtuple
from enum import Enum
from random import Random

from flask_jwt_extended import current_user
from jsonschema import validate as schema_validate, ValidationError
from sqlalchemy.orm import joinedload


import slobsterble.api_exceptions
from slobsterble.app import db
from slobsterble.constants import (
    BINGO_BONUS,
    TILES_ON_RACK_MAX,
)
from slobsterble.game_play_schema import TURN_PLAY_SCHEMA
from slobsterble.models import (
    Game,
    GamePlayer,
    Player,
    TileCount,
    PlayedTile,
    PositionedModifier,
    BoardLayout,
    Dictionary,
    Entry,
    Tile,
    Move,
)
from slobsterble.utilities.db_utilities import fetch_or_create
from slobsterble.utilities.tile_utilities import (
    build_tile_count_map,
    build_tile_object_map,
    fetch_all_tiles,
    fetch_mapped_tile_counts,
)


class Axis(Enum):
    ROW = 0
    COLUMN = 1


class StatelessValidator:
    """Manager for stateless validation."""

    def __init__(self, data):
        self.data = data
        self.validated = False

    def validate(self):
        """Perform all validation that is independent of the game state."""
        try:
            schema_validate(self.data, TURN_PLAY_SCHEMA)
        except ValidationError:
            raise slobsterble.api_exceptions.PlaySchemaException
        valid = self._validate_single_axis()
        self.validated = valid
        return valid

    def _validate_single_axis(self):
        """Validate that all tiles are played along a single axis."""
        row_set = set()
        column_set = set()
        for played_tile in self.data:
            if played_tile['row'] is not None:
                row_set.add(played_tile['row'])
            if played_tile['column'] is not None:
                column_set.add(played_tile['column'])
        if len(row_set) == 0 and len(column_set) == 0:
            return True
        if len(row_set) == 1:
            if len(column_set) != len(self.data):
                raise slobsterble.api_exceptions.PlayOverlapException()
            return True
        if len(column_set) == 1:
            if len(row_set) != len(self.data):
                raise slobsterble.api_exceptions.PlayOverlapException()
            return True
        raise slobsterble.api_exceptions.PlayAxisException()


GameBoardModifier = namedtuple(
    'GameBoardModifier', ['letter_multiplier', 'word_multiplier'])

GameBoardTile = namedtuple('GameBoardTile', ['letter', 'value'])


class GameBoard:
    """Convenient representation for a game board state."""
    def __init__(self, game_query):
        self.rows = game_query.board_layout.rows
        self.columns = game_query.board_layout.columns
        self.modifiers = [[GameBoardModifier(1, 1) for _ in range(self.columns)]
                          for _ in range(self.rows)]
        self.played_tiles = [[None for _ in range(self.columns)]
                             for _ in range(self.rows)]
        for positioned_modifier in game_query.board_layout.modifiers:
            row = positioned_modifier.row
            column = positioned_modifier.column
            letter_multiplier = positioned_modifier.modifier.letter_multiplier
            word_multiplier = positioned_modifier.modifier.word_multiplier
            self.modifiers[row][column] = GameBoardModifier(
                letter_multiplier=letter_multiplier,
                word_multiplier=word_multiplier)
        for played_tile in game_query.board_state:
            row = played_tile.row
            column = played_tile.column
            letter = played_tile.tile.letter
            value = played_tile.tile.value
            self.played_tiles[row][column] = GameBoardTile(
                letter=letter, value=value)


class StatefulValidator:
    """Manager for validation dependent on the game state."""

    def __init__(self, data, game_state, game_player):
        self.data = data
        self.game_id = game_state.id
        self.game_state = game_state
        self.game_board = GameBoard(self.game_state)
        self.game_player = game_player
        self.validated = False

    def validate(self):
        """Perform stateful validation."""
        valid = True
        valid &= self._validate_user_turn()
        valid &= self._validate_rack_tiles()
        valid &= self._validate_first_turn()
        valid &= self._validate_no_overlap()
        valid &= self._validate_connected()
        valid &= self._validate_contiguous()
        self.validated = valid
        return valid

    def _validate_user_turn(self):
        """Validate that it is the user's turn and return the game player."""
        if self.game_player is None or self.game_player.player.user_id != current_user.id:
            raise slobsterble.api_exceptions.PlayCurrentTurnException()
        return True

    def _validate_rack_tiles(self):
        """The current player must have the attempted played tiles."""
        rack_tiles = defaultdict(int)
        for tile_count in self.game_player.rack:
            tile = tile_count.tile
            tile_key = tile.letter, tile.value, tile.is_blank
            rack_tiles[tile_key] += tile_count.count
        for played_tile in self.data:
            is_blank = played_tile['is_blank']
            letter = None if is_blank else played_tile['letter'].upper()
            tile_key = letter, played_tile['value'], played_tile['is_blank']
            rack_tiles[tile_key] -= 1
            if rack_tiles[tile_key] < 0:
                raise slobsterble.api_exceptions.PlayRackTilesException()
        return True

    def _validate_first_turn(self):
        """
        The first turn must be an exchange, a pass, or a play through the centre.

        This assumes that the data has gone through stateless validation. In
        particular, it is assumed that there is not a mix of exchanged and
        played tiles.
        """
        centre_row = self.game_board.rows // 2
        centre_column = self.game_board.columns // 2
        if self.game_board.played_tiles[centre_row][centre_column] is None:
            if len(self.data) == 0 or self.data[0]['is_exchange']:
                return True
            for played_tile in self.data:
                if played_tile['row'] == centre_row \
                        and played_tile['column'] == centre_column:
                    return True
            raise slobsterble.api_exceptions.PlayFirstTurnException()

    def _validate_no_overlap(self):
        """The played tiles must not be in already occupied positions."""
        for played_tile in self.data:
            if not played_tile['is_exchange']:
                row = played_tile['row']
                column = played_tile['column']
                if self.game_board.played_tiles[row][column] is not None:
                    raise slobsterble.api_exceptions.PlayOverlapException()
        return True

    def _validate_connected(self):
        """
        The play must connect to an existing word, unless it is the first turn,
        an exchange, or a pass.

        This assumes that the data has gone through stateless validation. In
        particular, it is assumed that there is not a mix of exchanged and
        played tiles.
        """
        centre_row = self.game_board.rows // 2
        centre_column = self.game_board.columns // 2
        if self.game_board.played_tiles[centre_row][centre_column] is None:
            return True
        if len(self.data) == 0 or self.data[0]['is_exchange']:
            return True
        for played_tile in self.data:
            adjacent_deltas = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            for row_delta, column_delta in adjacent_deltas:
                adj_row = played_tile['row'] + row_delta
                adj_column = played_tile['column'] + column_delta
                if adj_row < 0 or adj_row >= self.game_board.rows \
                        or adj_column < 0 or adj_column >= self.game_board.columns:
                    continue
                if self.game_board.played_tiles[adj_row][adj_column] is not None:
                    return True
        raise slobsterble.api_exceptions.PlayConnectedException()

    def _validate_contiguous(self):
        """
        The played tiles, together with the board state, must be contiguous.

        This assumes that the data has gone through stateless validation. In
        particular, it is assumed that there is not a mix of exchanged and
        played tiles.
        """
        if len(self.data) <= 1 or self.data[0]['is_exchange']:
            return True
        sorted_data = sorted(self.data, key=lambda tile: (tile['row'], tile['column']))
        row_delta = 0
        column_delta = 1
        row = sorted_data[0]['row']
        column = sorted_data[0]['column']
        if sorted_data[0]['column'] == sorted_data[1]['column']:
            row_delta = 1
            column_delta = 0
        data_index = 0
        while data_index < len(self.data):
            if self.data[data_index]['row'] == row \
                    and self.data[data_index]['column'] == column:
                data_index += 1
            elif self.game_board.played_tiles[row][column] is None:
                raise slobsterble.api_exceptions.PlayContiguousException()
            row += row_delta
            column += column_delta
        return True


class WordBuilder:
    """Manager for iterating over placed tiles and adjacent board tiles."""

    def __init__(self, data, game_board):
        self.data = data
        self.data_letters = {
            (tile.row, tile.column): tile.letter for tile in data}
        self.data_values = {
            (tile.row, tile.column): tile.letter for tile in data}
        self.game_board = game_board

    def get_played_words(self):
        """
        Get the words created by the turn.

        The primary word is the word along the axis on which more than one tile
        was played. If only one tile was played, the primary word is the longest
        word. If there is no longer word, then the primary word is the word
        along the row. Secondary words are all other words created by the turn.
        """
        if len(self.data) == 0 or self.data[0]['is_exchange']:
            return None, []
        if len(self.data) == 1:
            # Special case.
            row_word = self._build_axis(
                self.data[0]['row'], self.data[0]['column'], Axis.ROW)
            column_word = self._build_axis(
                self.data[0]['row'], self.data[0]['column'], Axis.COLUMN)
            if len(row_word) == 1 and len(column_word) == 1:
                # This only happens if one tile is played on the first turn.
                return row_word, []
            elif len(row_word) >= len(column_word):
                if len(column_word) > 1:
                    return row_word, [column_word]
                return row_word, []
            else:
                if len(row_word) > 1:
                    return column_word, [row_word]
                return column_word, []
        if self.data[0]['row'] == self.data[1]['row']:
            primary_word = self._build_axis(
                self.data[0]['row'], self.data[0]['column'], Axis.ROW)
            secondary_words = []
            for played_tile in self.data:
                column_word = self._build_axis(
                    played_tile['row'], played_tile['column'], Axis.COLUMN)
                if len(column_word) > 1:
                    secondary_words.append(column_word)
        else:
            primary_word = self._build_axis(
                self.data[0]['row'], self.data[0]['column'], Axis.COLUMN)
            secondary_words = []
            for played_tile in self.data:
                row_word = self._build_axis(
                    played_tile['row'], played_tile['column'], Axis.ROW)
                if len(row_word) > 1:
                    secondary_words.append(row_word)
        return primary_word, secondary_words

    def compute_score(self):
        """Calculate the score of a played turn."""
        if len(self.data) == 0 or self.data[0]['is_exchange']:
            return 0
        if len(self.data) == 1:
            row_score = self._score_axis(
                self.data[0]['row'], self.data[0]['column'], Axis.ROW)
            if (self.data[0]['row'] == self.game_board.rows // 2
                    and self.data[0]['column'] == self.game_board.columns // 2):
                # Special case for the first turn if a single letter is played.
                return row_score
            column_score = self._score_axis(
                self.data[0]['row'], self.data[0]['column'], Axis.COLUMN)
            return row_score + column_score
        primary_axis = Axis.ROW
        secondary_axis = Axis.COLUMN
        if self.data[0]['row'] != self.data[1]['row']:
            primary_axis, secondary_axis = secondary_axis, primary_axis
        score_sum = 0
        score_sum += self._score_axis(
            self.data[0]['row'], self.data[0]['column'], primary_axis)
        for played_tile in self.data:
            score_sum += self._score_axis(
                played_tile['row'], played_tile['column'], secondary_axis)
        if len(self.data) == TILES_ON_RACK_MAX:
            score_sum += BINGO_BONUS
        return score_sum

    def _build_axis(self, start_row, start_column, axis):
        """Build a word from the given start position along the given axis."""
        assert axis in ('row', 'column')
        word_deque = deque()
        if axis is Axis.ROW:
            delta_pairs = [(-1, 0), (1, 0)]
        elif axis is Axis.COLUMN:
            delta_pairs = [(0, -1), (0, 1)]
        else:
            raise ValueError('Non Axis value %s passed to _build_axis.')
        board_tiles = self.game_board.played_tiles
        for row_delta, column_delta in delta_pairs:
            row = start_row
            column = start_column
            if row_delta == 1:
                row = start_row + 1
            if column_delta == 1:
                column = start_column + 1
            while 0 <= row < self.game_board.rows \
                    and 0 <= column < self.game_board.columns:
                if (row, column) in self.data_letters:
                    if row_delta + column_delta < 0:
                        word_deque.appendleft(self.data_letters[(row, column)])
                    else:
                        word_deque.append(self.data_letters[(row, column)])
                elif board_tiles[row][column] is not None:
                    if row_delta + column_delta < 0:
                        word_deque.appendleft(board_tiles[row][column].letter)
                    else:
                        word_deque.append(board_tiles[row][column].letter)
                else:
                    break
                row += row_delta
                column += column_delta
        return ''.join(word_deque)

    def _score_axis(self, start_row, start_column, axis):
        """Get the score through the given position and axis."""
        delta_pairs = [(-1, 0), (1, 0)] if axis is Axis.ROW else [(0, -1), (0, 1)]
        board_tiles = self.game_board.played_tiles
        score_sum = 0
        word_multiplier = 1
        word_len = 0
        for row_delta, column_delta in delta_pairs:
            row = start_row
            column = start_column
            if row_delta == 1:
                row = start_row + 1
            if column_delta == 1:
                column = start_column + 1
            while 0 <= row < self.game_board.rows \
                    and 0 <= column < self.game_board.columns:
                if (row, column) in self.data_values:
                    score_sum += (self.data_values[(row, column)] * self.game_board.modifiers[row][column].letter_multiplier)
                    word_multiplier *= self.game_board.modifiers[row][column].word_multiplier
                elif board_tiles[row][column] is not None:
                    score_sum += board_tiles[row][column].value
                else:
                    break
                row += row_delta
                column += column_delta
                word_len += 1
        if (start_row == self.game_board.rows // 2
                and start_column == self.game_board.columns // 2) or word_len > 1:
            # Special case for the first turn if a single letter is played.
            return score_sum * word_multiplier
        return 0


class WordValidator:
    """Validator for verifying that words are in a given dictionary."""

    def __init__(self, words, dictionary_id):
        self.words = words
        self.dictionary_id = dictionary_id

    def validate(self):
        for word in self.words:
            if not db.session.query(Dictionary).filter(
                    Dictionary.id == self.dictionary_id).join(
                    Dictionary.entries).filter(Entry.word == word).exists():
                raise slobsterble.api_exceptions.PlayDictionaryException()
        return True


class StateUpdater:
    """Manager for updating the game state."""

    def __init__(self, *, data, game_state, game_player, turn_score, primary_word,
                 secondary_words, random_generator=None):
        self.data = data
        self.game_state = game_state
        self.game_player = game_player
        self.turn_score = turn_score
        self.primary_word = primary_word
        self.secondary_words = secondary_words
        self.random_generator = random_generator or Random()

        self.initial_rack_state = build_tile_count_map(self.game_player.rack)
        self.initial_bag_state = build_tile_count_map(self.game_state.bag_tiles)

    def update_state(self):
        """Update the state of the game with the current turn."""
        next_rack_state, next_bag_state = self._get_next_bag_and_rack()
        exchanged_state = self._get_exchanged()
        # Fetch and create required objects.
        all_tiles = fetch_all_tiles(db.session)
        tile_object_map = build_tile_object_map(all_tiles)
        tile_counts_union = next_rack_state | next_bag_state | \
            self.initial_rack_state | exchanged_state
        tile_count_object_map = fetch_mapped_tile_counts(
            db.session, tile_counts_union, tile_object_map)
        played_tiles = self._fetch_played_tiles(tile_object_map)

        # Assemble the required TileCount objects for the Game, Move, and
        # GamePlayer.
        initial_rack = [
            tile_count_object_map[(tile_key, count)]
            for tile_key, count in self.initial_rack_state.items()]
        exchanged_tiles = [
            tile_count_object_map[(tile_key, count)]
            for tile_key, count in exchanged_state]
        next_rack = [
            tile_count_object_map[(tile_key, count)]
            for tile_key, count in next_rack_state.items()]
        next_bag_tiles = [
            tile_count_object_map[(tile_key, count)]
            for tile_key, count in next_bag_state.items()]
        played_time = datetime.datetime.utcnow()
        # Create the move object.
        move = Move(
            game_player_id=self.game_player.id, primary_word=self.primary_word,
            secondary_words=','.join(self.secondary_words),
            rack_tiles=initial_rack, exchanged_tiles=exchanged_tiles,
            turn_number=self.game_state.turn_number, score=self.turn_score,
            played_time=played_time)
        db.session.add(move)
        # Update the game state.
        self.game_player.rack = next_rack
        self.game_state.bag_tiles = next_bag_tiles
        self.game_player.score += self.turn_score
        self.game_state.board_state.extend(played_tiles)
        self.game_state.turn_number += 1
        if not self.game_player.rack and not self.game_state.bag_tiles:
            self.game_state.completed = played_time
            remaining_sum = 0
            for game_player in self.game_state.game_players:
                player_rack_tile_sum = sum(
                    tile_count.tile.value * tile_count.count
                    for tile_count in game_player.rack)
                game_player.score -= player_rack_tile_sum
                remaining_sum += player_rack_tile_sum
            self.game_player.score += remaining_sum
        db.session.commit()

    def _get_next_bag_and_rack(self):
        """Get the rack and bag state after placing and drawing tiles."""
        next_rack_state = self.initial_rack_state.copy()
        next_bag_state = self.initial_bag_state.copy()
        for played_tile in self.data:
            tile_key = (played_tile['letter'], played_tile['value'],
                        played_tile['is_blank'])
            next_rack_state[tile_key] -= 1
            if played_tile['is_exchange']:
                next_rack_state[tile_key] += 1
        num_tiles_in_bag = sum(next_bag_state.values())
        num_tiles_on_rack = sum(next_rack_state.values())
        num_tiles_to_draw = min(
            TILES_ON_RACK_MAX - num_tiles_on_rack, num_tiles_in_bag)
        tile_keys = []
        counts = []
        for tile_key, count in next_bag_state.items():
            tile_keys.append(tile_key)
            counts.append(count)
        if num_tiles_to_draw > 0:
            drawn_tiles = self.random_generator.sample(
                tile_keys, counts=counts, k=num_tiles_to_draw)
        else:
            drawn_tiles = []
        for tile_key in drawn_tiles:
            next_bag_state[tile_key] -= 1
            next_rack_state[tile_key] += 1
        return next_rack_state, next_bag_state

    def _get_exchanged(self):
        """Get the tiles that were exchanged as a dict of tile_keys to ints."""
        if len(self.data) == 0 or not self.data[0]['is_exchange']:
            return {}
        exchanged_tiles = defaultdict(int)
        for exchanged_tile in self.data:
            tile_key = (
                exchanged_tile['letter'], exchanged_tile['value'],
                exchanged_tile['is_blank'])
            exchanged_tiles[tile_key] += 1
        return exchanged_tiles

    def _fetch_played_tiles(self, tile_object_map):
        """
        Fetch the PlayedTile objects for tiles placed on the board.

        If a PlayedTile object does not exist in the database, it will be
        created.
        """
        if len(self.data) == 0 or self.data[0]['is_exchange']:
            return []
        played_tiles = []
        for datum in self.data:
            tile_key = (datum['letter'], datum['value'], datum['is_blank'])
            row = datum['row']
            column = datum['column']
            if tile_key not in tile_object_map:
                tile_object_map[tile_key] = fetch_or_create(
                    db.session, Tile,
                    letter=tile_key[0], value=tile_key[1], is_blank=tile_key[2])
            played_tile = fetch_or_create(
                db.session, PlayedTile,
                tile_id=tile_object_map[tile_key], row=row, column=column)
            played_tiles.append(played_tile)
        return played_tiles


def get_game_player(game_state):
    """Get the game player whose turn it is to play."""
    num_players = len(game_state.game_players)
    for game_player in game_state.game_players:
        if game_state.turn_number % num_players == game_player.turn_order:
            return game_player
    return None


def fetch_game_state(game_id):
    """Fetch all data, except dictionary lookups, needed for turn validation."""
    game_state = db.session.query(Game).filter(Game.id == game_id).options(
        joinedload(Game.game_players).options(
            joinedload(GamePlayer.player).joinedload(Player.user),
            joinedload(GamePlayer.rack).joinedload(TileCount.tile)),
        joinedload(Game.board_state).joinedload(PlayedTile.tile),
        joinedload(Game.bag_tiles).joinedload(TileCount.tile),
        joinedload(Game.board_layout).joinedload(
            BoardLayout.modifiers).joinedload(PositionedModifier.modifier),
    ).one()
    return game_state


