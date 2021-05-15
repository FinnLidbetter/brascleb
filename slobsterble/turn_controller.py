"""Controller for updating a game state."""

import datetime
import random
from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import aliased, joinedload, subqueryload

from slobsterble.app import db
from slobsterble.constants import (
    BINGO_BONUS,
    GAME_COLUMNS_MAX,
    GAME_ROWS_MAX,
    PLAYED_TILE_REQUIRED_FIELDS,
    TILE_VALUE_MAX,
    TILES_ON_RACK_MAX,
)
from slobsterble.models import (
    BoardLayout,
    Dictionary,
    Game,
    GamePlayer,
    Move,
    PlayedTile,
    Player,
    PositionedModifier,
    Tile,
    TileCount,
    User)


def _validate_bool(value, allow_none):
    """Validate that the given value is either 'True', or 'False', or None."""
    if allow_none and value is None:
        return True
    return value is True or value is False


def _validate_int(value, value_min, value_max, allow_none):
    """Validate that the given value is an int within the specified bounds."""
    if allow_none and value is None:
        return True
    try:
        cast_value = int(value)
        return value_min <= cast_value <= value_max
    except ValueError:
        return False


def _validate_alpha_character(value, require_lower=False,
                              require_upper=False, allow_none=False):
    """Validate that the given value is a single alphabetic character."""
    if allow_none and value is None:
        return True
    if not isinstance(value, str):
        return False
    if len(value) != 1:
        return False
    if not value.isalpha():
        return False
    if require_lower and value.lower() != value:
        return False
    if require_upper and value.upper() != value:
        return False
    return True


def _validate_played_tile(played_tile, index, errors):
    """Validate that the tile data has the expected types and value ranges."""
    for field in PLAYED_TILE_REQUIRED_FIELDS:
        if field not in played_tile:
            errors.append('Tile %d is Missing field %s' % (index, str(field)))
            return False
    if len(played_tile) > len(PLAYED_TILE_REQUIRED_FIELDS):
        errors.append('Tile %d has too many fields' % index)
        return False
    if not _validate_int(played_tile['row'],
                         0, GAME_ROWS_MAX - 1,
                         allow_none=True):
        errors.append('Tile %d has a bad row value.' % index)
        return False
    if not _validate_int(played_tile['column'],
                         0, GAME_COLUMNS_MAX - 1,
                         allow_none=True):
        errors.append('Tile %d has a bad column value.' % index)
        return False
    if not _validate_int(played_tile['value'],
                         0, TILE_VALUE_MAX,
                         allow_none=False):
        errors.append("Tile %d has a bad 'value' value." % index)
        return False
    if not _validate_alpha_character(played_tile['letter'], allow_none=True):
        errors.append('Tile %d has a non-alphabetic letter.' % index)
        return False
    if not _validate_bool(played_tile['is_blank'], allow_none=False):
        errors.append("Tile %d has non-bool 'is_blank'." % index)
        return False
    if not _validate_bool(played_tile['is_exchange'], allow_none=False):
        errors.append("Tile %d has non-bool 'is_exchange'." % index)
        return False
    return True


def mutate_data(data):
    """
    Convert values to python types and standardise letters as uppercase.

    This function assumes that the data has been validated.
    """
    for played_tile in data['played_tiles']:
        played_tile['is_blank'] = played_tile['is_blank'] == 'True'
        played_tile['is_exchange'] = played_tile['is_exchange'] == 'True'
        played_tile['value'] = int(played_tile['value'])
        if played_tile['row'] is not None:
            played_tile['row'] = int(played_tile['row'])
        if played_tile['column'] is not None:
            played_tile['column'] = int(played_tile['column'])
        if played_tile['letter'] is not None:
            played_tile['letter'] = played_tile['letter'].upper()


def validate_play_data(data, errors):
    """Validate that the play data is formatted as expected."""
    if 'played_tiles' not in data:
        errors.append("Missing 'played_tiles' key.")
        return False
    data_played_tiles = data['played_tiles']
    if not isinstance(data_played_tiles, list):
        return False, "'played_tiles' is not a list."
    for index, played_tile in enumerate(data_played_tiles):
        if not _validate_played_tile(played_tile, index, errors):
            return False
    return True


def validate_plausible_data(data, errors):
    """
    Check that tiles are played on a single axis in distinct cells or exchanged.

    Assumes that data has been parsed to have the expected types.
    """
    row_set = set()
    column_set = set()
    exchanged_count = 0
    tiles_played = len(data['played_tiles'])
    if len(data['played_tiles']) == 0:
        return True
    for played_tile in data['played_tiles']:
        row_set.add(played_tile['row'])
        column_set.add(played_tile['column'])
        if played_tile['is_exchange']:
            exchanged_count += 1
        elif played_tile['letter'] is None:
            # Letter can only be None if it is a blank tile being exchanged.
            errors.append('Non-exchanged played tile has a blank letter.')
            return False
    if exchanged_count > 0:
        if exchanged_count != len(data['played_tiles']):
            errors.append('At least one played tile was marked as an exchange.')
            return False
        return True
    if (len(row_set) == 1 and len(column_set) == tiles_played) or (
            len(column_set) == 1 and len(row_set) == tiles_played):
        return True
    errors.append('Tiles not played on a single axis.')
    return False


def validate_user_turn(current_user, game_id):
    """Return true iff it is current_user's turn in the given game."""
    game_query = db.session.query(Game).filter(Game.id == game_id).options(
        joinedload(Game.game_player_to_play).joinedload(
        GamePlayer.player).joinedload(Player.user)).first()
    if game_query is None:
        # The queried game does not exist.
        return False
    if game_query.completed is not None:
        # The game is completed.
        return False
    return game_query.game_player_to_play.player.user.id == current_user.id


def _validate_player_has_tiles(game_query, data):
    """Validate that the player has the tiles played."""
    played_tile_counts = defaultdict(lambda: defaultdict(int))
    exchange_count = 0
    for played_tile in data['played_tiles']:
        letter = played_tile['letter']
        value = played_tile['value']
        if played_tile['is_blank']:
            letter = None
        else:
            letter = letter.upper()
        if played_tile['is_exchange']:
            exchange_count += 1
        played_tile_counts[letter][value] += 1
    rack = game_query.game_player_to_play.rack
    rack_tile_counts = defaultdict(lambda: defaultdict(int))
    for tile_count in rack:
        letter = tile_count.tile.letter
        if letter is not None:
            letter = letter.upper()
        value = tile_count.tile.value
        rack_tile_counts[letter][value] += tile_count.count
    for letter in played_tile_counts:
        for value in played_tile_counts[letter]:
            if letter not in rack_tile_counts:
                return False
            if value not in rack_tile_counts[letter]:
                return False
            if rack_tile_counts[letter][value] < \
                    played_tile_counts[letter][value]:
                return False
    return True


def _get_game_grid_letters(game_query):
    """Get the current board state as a 2-D array."""
    rows = game_query.board_layout.rows
    columns = game_query.board_layout.columns
    grid = [[None for _ in range(columns)] for _ in range(rows)]
    for played_tile in game_query.board_state:
        grid[played_tile.row][played_tile.column] = played_tile.tile.letter
    return grid


def _get_game_grid_values(game_query):
    """Get the current board state as a 2-D array."""
    rows = game_query.board_layout.rows
    columns = game_query.board_layout.columns
    grid = [[None for _ in range(columns)] for _ in range(rows)]
    for played_tile in game_query.board_state:
        grid[played_tile.row][played_tile.column] = played_tile.tile.value
    return grid


def _get_center(game_query):
    """Get the center row and column."""
    rows = game_query.board_layout.rows
    columns = game_query.board_layout.columns
    return rows // 2, columns // 2


def _get_game_grid_modifiers(game_query):
    """Get the word and letter modifiers for the game."""
    rows = game_query.board_layout.rows
    columns = game_query.board_layout.columns
    word_multipliers = [[1 for _ in range(columns)] for _ in range(rows)]
    letter_multipliers = [[1 for _ in range(columns)] for _ in range(columns)]
    for positioned_modifier in game_query.board_layout.modifiers:
        row = positioned_modifier.row
        column = positioned_modifier.column
        word_multiplier = positioned_modifier.modifier.word_multiplier
        letter_multiplier = positioned_modifier.modifier.letter_multiplier
        word_multipliers[row][column] = word_multiplier
        letter_multipliers[row][column] = letter_multiplier
    return word_multipliers, letter_multipliers


def _is_exchange_or_pass(data):
    """Return True iff the there all played tiles are exchanged."""
    return all([tile['is_exchange'] for tile in data['played_tiles']])


def _validate_cells_available(grid, data):
    """Validate that the cells that the tiles are played in are empty."""
    for played_tile in data['played_tiles']:
        if played_tile['row'] >= len(grid):
            return False
        if played_tile['column'] >= len(grid[played_tile['row']]):
            return False
        if grid[played_tile['row']][played_tile['column']] is not None:
            return False
    return True


def _validate_continuous(grid, data):
    """
    Validate that the tiles played form a continous sequence of tiles.

    Assumes that the played tiles are along a single axis in distinct
    empty cells.
    """
    row_set = set()
    column_set = set()
    for played_tile in data['played_tiles']:
        row_set.add(played_tile['row'])
        column_set.add(played_tile['column'])
    if len(row_set) == 1:
        played_column_min = min(column_set)
        played_column_max = max(column_set)
        row = row_set.pop()
        for column in range(played_column_min, played_column_max + 1):
            if column not in column_set and grid[row][column] is None:
                return False
        return True
    played_row_min = min(row_set)
    played_row_max = max(row_set)
    column = column_set.pop()
    for row in range(played_row_min, played_row_max + 1):
        if row not in row_set and grid[row][column] is None:
            return False
    return True


def _is_first_turn(data, center_row, center_column):
    """Return True iff the played tiles go through the center cell."""
    for played_tile in data['played_tiles']:
        if played_tile['row'] == center_row and \
                played_tile['column'] == center_column:
            return True
    return False


def _validate_connects(grid, data):
    """Return True iff a played tile is adjacent to a tile on the board."""
    row_offsets = [0, 0, 1, -1]
    column_offsets = [1, -1, 0, 0]
    for played_tile in data['played_tiles']:
        row = played_tile['row']
        column = played_tile['column']
        for d_row, d_column in zip(row_offsets, column_offsets):
            adjacent_row = row + d_row
            adjacent_column = column + d_column
            if 0 <= adjacent_row < len(grid) and \
                    0 <= adjacent_column < len(grid[adjacent_row]):
                if grid[adjacent_row][adjacent_column] is not None:
                    return True
    return False


def _get_word_row_endpoints(grid, played_tile_map, row, column):
    """Get the min and max rows connected to the tile in the given column."""
    row_min = row
    while row_min > 0:
        if grid[row_min - 1][column] is not None or \
                played_tile_map.get(row_min - 1, {}).get(column) is not None:
            row_min -= 1
        else:
            break
    row_max = row
    while row_max < len(grid) - 1:
        if grid[row_max + 1][column] is not None or \
                played_tile_map.get(row_max + 1, {}).get(column) is not None:
            row_max += 1
        else:
            break
    return row_min, row_max


def _get_word_column_endpoints(grid, played_tile_map, row, column):
    """Get the min and max columns connected to the tile in the given row."""
    column_min = column
    while column_min > 0:
        if grid[row][column_min - 1] is not None or \
                played_tile_map.get(row, {}).get(column_min - 1) is not None:
            column_min -= 1
        else:
            break
    column_max = column
    while column_max < len(grid[row]) - 1:
        if grid[row][column_max + 1] is not None or \
                played_tile_map.get(row, {}).get(column_max + 1) is not None:
            column_max += 1
        else:
            break
    return column_min, column_max


def _read_word(grid, played_tile_map, row_min, row_max, column_min, column_max):
    """
    Read a word from the grid and played tiles.

    Assumes that either row_min == row_max or column_min == column_max.
    """
    if row_min == row_max:
        return ''.join(grid[row_min][column] or played_tile_map[row_min][column]
                       for column in range(column_min, column_max + 1))
    return ''.join(grid[row][column_min] or played_tile_map[row][column_min]
                   for row in range(row_min, row_max + 1))


def _get_words(grid, data):
    """Get a list of the new words created and the primary word played."""
    center_row = len(grid) // 2
    center_column = len(grid[0]) // 2
    if len(data['played_tiles']) == 0 or data['played_tiles'][0]['is_exchange']:
        # Either the turn was passed or tiles were exchanged.
        return [], None
    if len(data['played_tiles']) == 1:
        # Special case where a single letter word is played on the first turn.
        row = data['played_tiles'][0]['row']
        column = data['played_tiles'][0]['column']
        if row == center_row and column == center_column:
            letter = data['played_tiles'][0]['letter']
            return [letter], letter
    row_set = set()
    column_set = set()
    played_letters_map = defaultdict(dict)
    for played_tile in data['played_tiles']:
        row = played_tile['row']
        column = played_tile['column']
        row_set.add(row)
        column_set.add(column)
        played_letters_map[row][column] = played_tile['letter']
    words = []
    primary_word = None
    for row in row_set:
        column = column_set.pop()
        column_set.add(column)
        column_min, column_max = _get_word_column_endpoints(
            grid, played_letters_map, row, column)
        word = _read_word(
            grid, played_letters_map, row, row, column_min, column_max)
        if len(word) > 1:
            words.append(word)
        if len(row_set) == 1:
            primary_word = word
    for column in column_set:
        row = row_set.pop()
        row_set.add(row)
        row_min, row_max = _get_word_row_endpoints(
            grid, played_letters_map, row, column)
        word = _read_word(
            grid, played_letters_map, row_min, row_max, column, column)
        if len(word) > 1:
            words.append(word)
        if len(column_set) == 1:
            primary_word = word
    return words, primary_word


def _get_invalid_words(words, game_query_result):
    """Validate that the played words are in the dictionary."""
    invalid_words = []
    dictionary_words = set(
        entry.word.upper() for entry in game_query_result.dictionary.entries)
    for word in words:
        if word not in dictionary_words:
            invalid_words.append(word)
    return invalid_words


def validate_play(game_id, data, errors):
    """
    Return true iff the play is a legal use of the player's tiles.

    Assumes:
    - The data has been validated and mutated as expected.
    - It is the current_user's turn.
    """
    RackTile = aliased(Tile)
    BoardTile = aliased(Tile)
    game_query = db.session.query(Game).filter(Game.id == game_id).join(
        Game.game_player_to_play).join(GamePlayer.player).join(
        Player.user).outerjoin(GamePlayer.rack).outerjoin(
        RackTile, TileCount.tile).outerjoin(Game.board_state).outerjoin(
        BoardTile, PlayedTile.tile).join(
        Game.dictionary).join(Dictionary.entries).options(
        joinedload(Game.game_player_to_play).subqueryload(
        GamePlayer.rack).joinedload(TileCount.tile)).options(
        subqueryload(Game.board_state).joinedload(PlayedTile.tile)).options(
        joinedload(Game.dictionary).subqueryload(Dictionary.entries)).options(
        joinedload(Game.board_layout))
    game_query_result = game_query.first()
    if not _validate_player_has_tiles(game_query_result, data):
        errors.append('Player attempted to use a tile that they do not have.')
        return False, None, []
    if _is_exchange_or_pass(data):
        return True, None, []
    game_grid = _get_game_grid_letters(game_query_result)
    if not _validate_cells_available(game_grid, data):
        errors.append('Player attempted to play in an occupied space.')
        return False, None, []
    if not _validate_continuous(game_grid, data):
        errors.append('Your tiles were not played continuously.')
        return False, None, []
    center_row, center_column = _get_center(game_query_result)
    if not _is_first_turn(data, center_row, center_column) and not _validate_connects(game_grid, data):
        errors.append('Your tiles do not join onto the played words correctly.')
        return False, None, []
    words_played, primary_word = _get_words(game_grid, data)
    invalid_words = _get_invalid_words(words_played, game_query_result)
    if invalid_words:
        for invalid_word in invalid_words:
            errors.append('%s is not in the dictionary.' % invalid_word)
        return False, None, []
    # Move the primary word to the front of the list.
    for word_index in range(len(words_played)):
        if words_played[word_index] == primary_word:
            words_played[0], words_played[word_index] = \
                words_played[word_index], words_played[0]
            break
    return True, primary_word, words_played[1:]


def score_play(game_id, data):
    """Get the score of the play."""
    if not data['played_tiles'] or data['played_tiles'][0]['is_exchange']:
        return 0
    game_query = db.session.query(Game).filter(Game.id == game_id).outerjoin(
        Game.board_state).outerjoin(PlayedTile.tile).options(
        subqueryload(Game.board_state).joinedload(PlayedTile.tile)).options(
        joinedload(Game.board_layout).subqueryload(
            BoardLayout.modifiers).joinedload(PositionedModifier.modifier))
    game_query_result = game_query.first()
    game_grid = _get_game_grid_values(game_query_result)
    word_modifiers, letter_modifiers = _get_game_grid_modifiers(
        game_query_result)
    center_row, center_column = _get_center(game_query_result)
    row_set = set()
    column_set = set()
    played_values_map = defaultdict(dict)
    for played_tile in data['played_tiles']:
        row = played_tile['row']
        column = played_tile['column']
        row_set.add(row)
        column_set.add(column)
        played_values_map[row][column] = played_tile['value']
    if (len(row_set) == 1 and len(column_set) == 1 and
            played_values_map.get(center_row, {}).get(center_column)
            is not None):
        # Handle the special case where a single letter is played
        # on the first turn.
        return (letter_modifiers[center_row][center_column]
                * word_modifiers[center_row][center_column]
                * played_values_map.get(center_row, {}).get(center_column))
    score_sum = 0
    for row in row_set:
        column = column_set.pop()
        column_set.add(column)
        column_min, column_max = _get_word_column_endpoints(
            game_grid, played_values_map, row, column)
        if column_min < column_max:
            word_score = 0
            word_multiplier = 1
            for column in range(column_min, column_max + 1):
                played_tile_value = played_values_map.get(row, {}).get(column)
                if played_tile_value is not None:
                    word_score += (played_tile_value
                                   * letter_modifiers[row][column])
                    word_multiplier *= word_modifiers[row][column]
                else:
                    word_score += game_grid[row][column]
            word_score *= word_multiplier
            score_sum += word_score
    for column in column_set:
        row = row_set.pop()
        row_set.add(row)
        row_min, row_max = _get_word_row_endpoints(
            game_grid, played_values_map, row, column)
        if row_min < row_max:
            word_score = 0
            word_multiplier = 1
            for row in range(row_min, row_max + 1):
                played_tile_value = played_values_map.get(row, {}).get(column)
                if played_tile_value is not None:
                    word_score += (played_tile_value
                                   * letter_modifiers[row][column])
                    word_multiplier *= word_modifiers[row][column]
                else:
                    word_score += game_grid[row][column]
            word_score *= word_multiplier
            score_sum += word_score
    if len(data['played_tiles']) == TILES_ON_RACK_MAX:
        score_sum += BINGO_BONUS
    return score_sum


def place_tiles(game_id, data):
    """
    Update the database state with the tiles placed in this game.

    Note that this function does not update the player's rack state.
    """
    if not data['played_tiles'] or data['played_tiles'][0]['is_exchange']:
        # If the turn was an exchange or pass then there are no tiles to place.
        return
    game = db.session.query(Game).filter(Game.id == game_id).options(
        subqueryload(Game.board_state)).first()
    for tile_to_place in data['played_tiles']:
        letter = tile_to_place['letter']
        value = tile_to_place['value']
        is_blank = tile_to_place['is_blank']
        row = tile_to_place['row']
        column = tile_to_place['column']
        # Tile should always exist, else something has gone horribly wrong.
        tile = db.session.query(Tile).filter_by(
            letter=letter, value=value, is_blank=is_blank).first()
        played_tile = db.session.query(PlayedTile).filter_by(
            row=row, column=column, tile_id=tile.id).first()
        if played_tile is None:
            played_tile = PlayedTile(row=row, column=column, tile=tile)
            db.session.add(played_tile)
        game.board_state.append(played_tile)


def add_turn_score_and_move(game_id, turn_score,
                            primary_word, secondary_words, data):
    """Add the given value to the current player's score."""
    game = db.session.query(Game).filter(Game.id == game_id).options(
        joinedload(Game.game_player_to_play)).first()
    game_player = game.game_player_to_play
    game_player.score = game_player.score + turn_score
    if not primary_word:
        move = Move(game_player=game_player,
                    primary_word=None,
                    secondary_words=None,
                    exchanged_tiles=len(data['played_tiles']),
                    turn_number=game.turn_number,
                    score=0,
                    played_time=func.now())
    else:
        move = Move(game_player=game_player,
                    primary_word=primary_word,
                    secondary_words=', '.join(secondary_words),
                    exchanged_tiles=0,
                    turn_number=game.turn_number,
                    score=turn_score,
                    played_time=func.now())
    db.session.add(move)


def draw_tiles(game_id, data):
    """Remove tiles from the rack and draw tiles from the bag."""
    game = db.session.query(Game).filter(Game.id == game_id).options(
        subqueryload(Game.bag_tiles)).options(
        joinedload(Game.game_player_to_play).subqueryload(GamePlayer.rack)).first()
    tile_counts = db.session.query(TileCount).options(
        joinedload(TileCount.tile)).all()
    tile_count_dict = {(tile_count.tile_id, tile_count.count): tile_count
                       for tile_count in tile_counts}
    tile_dict = {(tile_count.tile.letter, tile_count.tile.value): tile_count.tile
                 for tile_count in tile_counts}
    bag_tiles_with_repeats = []
    for tile_count in game.bag_tiles:
        for _ in range(tile_count.count):
            bag_tiles_with_repeats.append(tile_count.tile_id)
    if data['played_tiles'] and data['played_tiles'][0]['is_exchange']:
        for played_tile in data['played_tiles']:
            tile_key = (played_tile['letter'], played_tile['value'])
            tile_id = tile_dict[tile_key].id
            bag_tiles_with_repeats.append(tile_id)
    num_tiles_to_draw = min(len(data['played_tiles']),
                            len(bag_tiles_with_repeats))
    chosen_tile_ids = random.sample(bag_tiles_with_repeats, k=num_tiles_to_draw)
    rack_tile_counts = game.game_player_to_play.rack
    bag_tile_counts = game.bag_tiles
    rack_state = {tile_count.tile_id: tile_count.count
                  for tile_count in rack_tile_counts}
    bag_state = {tile_count.tile_id: tile_count.count
                 for tile_count in bag_tile_counts}
    for played_tile in data['played_tiles']:
        letter = played_tile['letter']
        value = played_tile['value']
        is_blank = played_tile['is_blank']
        if is_blank:
            letter = None
        tile_key = (letter, value)
        tile_id = tile_dict[tile_key].id
        rack_state[tile_id] -= 1
    for chosen_tile_id in chosen_tile_ids:
        if chosen_tile_id in rack_state:
            rack_state[chosen_tile_id] += 1
        else:
            rack_state[chosen_tile_id] = 1
        bag_state[chosen_tile_id] -= 1
    rack_keys_to_remove = []
    bag_keys_to_remove = []
    for tile_id in rack_state:
        if rack_state[tile_id] == 0:
            rack_keys_to_remove.append(tile_id)
    for key in rack_keys_to_remove:
        del rack_state[key]
    for tile_id in bag_state:
        if bag_state[tile_id] == 0:
            bag_keys_to_remove.append(tile_id)
    for key in bag_keys_to_remove:
        del bag_state[key]
    rack_tile_counts = [tile_count_dict[(tile_id, count)]
                        for tile_id, count in rack_state.items()]
    bag_tile_counts = [tile_count_dict[(tile_id, count)]
                       for tile_id, count in bag_state.items()]
    game.game_player_to_play.rack = rack_tile_counts
    game.bag_tiles = bag_tile_counts
    if len(bag_tile_counts) == 0 and len(rack_tile_counts) == 0:
        return False
    return True


def tally_remaining_tiles(game_id):
    game = db.session.query(Game).filter(Game.id == game_id).options(
        subqueryload(Game.game_players).subqueryload(
        GamePlayer.rack).joinedload(TileCount.tile)).options(
        joinedload(Game.game_player_to_play).joinedload(GamePlayer.player)).first()
    remaining_sum = 0
    for game_player in game.game_players:
        if game_player == game.game_player_to_play:
            continue
        player_tile_sum = 0
        for tile_count in game_player.rack:
            player_tile_sum += tile_count.tile.value * tile_count.count
        game_player.score -= player_tile_sum
        remaining_sum += player_tile_sum
    game.game_player_to_play.score += remaining_sum
    winning_score = max(game_player.score for game_player in game.game_players)
    num_winners = 0
    for game_player in game.game_players:
        if game_player.score == winning_score:
            num_winners += 1
    for game_player in game.game_players:
        if game_player.score == winning_score:
            if num_winners == 1:
                game_player.player.wins += 1
            else:
                game_player.player.ties += 1
        else:
            game_player.player.losses += 1


def set_completed_time(game_id):
    game = db.session.query(Game).filter(Game.id == game_id).first()
    game.completed = datetime.datetime.now()


def advance_turn(game_id):
    game = db.session.query(Game).filter(Game.id == game_id).options(
        subqueryload(Game.game_players)).options(
        joinedload(Game.game_player_to_play)).first()
    game.turn_number += 1
    for game_player in game.game_players:
        if game.turn_number % len(game.game_players) == game_player.turn_order:
            game.game_player_to_play = game_player
            break
