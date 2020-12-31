"""API views."""
import json
import random

from flask import Blueprint, Response, jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload, subqueryload

from slobsterble import db
from slobsterble.constants import (
    ACTIVE_GAME_LIMIT,
    FRIEND_KEY_CHARACTERS,
    FRIEND_KEY_LENGTH,
    GAME_PLAYERS_MAX)
from slobsterble.forms import (
    AddWordForm,
    NewGameForm,
    TemporaryPlayForm,
    set_dictionary_choices,
    set_opponent_choices,
)
from slobsterble.game_setup_controller import (
    initialize_bag,
    initialize_racks
)
from slobsterble.turn_controller import (
    advance_turn,
    add_turn_score_and_move,
    draw_tiles,
    place_tiles,
    score_play,
    tally_remaining_tiles,
    validate_plausible_data,
    validate_play,
    validate_play_data,
    validate_user_turn,
)
from slobsterble.models import (
    Dictionary,
    Entry,
    Game,
    GamePlayer,
    Move,
    PlayedTile,
    Player,
    Role,
    Tile,
    TileCount,
    User,
)


bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/games', methods=['GET'])
@login_required
def get_games():
    """Get in progress games."""
    user_active_players = db.session.query(GamePlayer).join(
        GamePlayer.player).join(Player.user).filter(
        User.id == current_user.id).join(GamePlayer.game).order_by(
        Game.started.desc()).limit(ACTIVE_GAME_LIMIT).subquery()
    user_active_games = db.session.query(Game).join(
        user_active_players, Game.id == user_active_players.c.game_id).join(
        Game.game_players).join(GamePlayer.player).options(
        subqueryload(Game.game_players).joinedload(GamePlayer.player))
    serialized_games = Game.serialize_list(
        user_active_games.all(),
        override_mask={Game: ['started', 'completed', 'whose_turn_name',
                              'game_players', 'id'],
                       GamePlayer: ['score', 'player'],
                       Player: ['display_name']})
    return jsonify({'games': serialized_games})


@bp.route('/game/<int:game_id>', methods=['GET'])
@login_required
def get_game(game_id):
    """
    Get the current state of the game.

    This includes:
    - The played tiles.
    - The names and scores of the other players.
    - The logged in user's rack tiles.
    - The number of tiles remaining.
    - Whose turn it is.
    """
    game_query = db.session.query(Game).filter(Game.id == game_id).join(
        Game.game_players).join(GamePlayer.player).join(Player.user).outerjoin(
        Game.board_state).options(subqueryload(Game.board_state).joinedload(
        PlayedTile.tile)).options(subqueryload(Game.game_players).joinedload(
        GamePlayer.player).joinedload(Player.user))
    if game_query.count() == 0:
        # The game does not exist.
        return Response('Game with this ID not found.', status=404)
    if game_query.filter(User.id == current_user.id).count() == 0:
        # The user is not part of this game.
        return Response('User is not authorized to access this game.', status=401)
    serialized_game_state = game_query.first().serialize(
        override_mask={Game: ['board_state', 'game_players',
                              'whose_turn_name', 'num_tiles_remaining'],
                       GamePlayer: ['score', 'player'],
                       Player: ['display_name'],
                       PlayedTile: ['tile', 'row', 'column'],
                       Tile: ['letter', 'is_blank', 'value']})
    user_rack = db.session.query(GamePlayer).filter(
        GamePlayer.game_id == game_id).join(GamePlayer.player).join(
        Player.user).filter(Player.user_id == current_user.id).join(
        GamePlayer.rack).join(TileCount.tile).options(
        subqueryload(GamePlayer.rack).joinedload(TileCount.tile)).first()
    serialized_user_rack = user_rack.serialize(
        override_mask={GamePlayer: ['rack'],
                       TileCount: ['tile', 'count'],
                       Tile: ['letter', 'is_blank', 'value']})
    serialized_game_state['rack'] = serialized_user_rack['rack']
    return jsonify(serialized_game_state)


#@bp.route('/game/<int:game_id>/move-history', methods=['GET'])
#@login_required
#def move_history(game_id):
#    """Get the history of turns for a game."""



@bp.route('/game/<int:game_id>/verify-word/<string:word>', methods=['GET'])
@login_required
def verify_word(game_id, word):
    """Verify if a word is in the game's dictionary."""
    game_query = db.session.query(Game).filter(Game.id == game_id).join(
        Game.game_players).join(GamePlayer.player).join(Player.user)
    if game_query.count() == 0:
        # The game does not exist.
        return Response('No game with ID %d.' % game_id, status=400)
    if game_query.filter(User.id == current_user.id).count() == 0:
        # The user is not part of this game.
        return Response('User is not authorized.', status=401)
    word_lookup = db.session.query(Game).join(Game.dictionary).join(
        Dictionary.entries).filter(
        func.lower(Entry.word) == func.lower(word)).options(
        joinedload(Game.dictionary).subqueryload(Dictionary.entries)).first()
    if word_lookup is None:
        return {}
    return jsonify(entry=word_lookup.dictionary.entries[0].serialize())


@bp.route('/game/<int:game_id>/play', methods=['GET', 'POST'])
@login_required
def play(game_id):
    """API to play a turn of the game."""
    data = request.get_json()
    errors = []
    is_valid_data = validate_play_data(data, errors)
    if not is_valid_data:
        return Response('Invalid data: %s.' % str(errors), status=400)
    is_plausible_data = validate_plausible_data(data, errors)
    if not is_plausible_data:
        return Response('Invalid data: %s.' % str(errors), status=400)
    is_current_user_turn = validate_user_turn(current_user, game_id)
    if not is_current_user_turn:
        return Response('It is not your turn', status=403)
    valid, primary_word, secondary_words = validate_play(game_id, data, errors)
    if not valid:
        return Response('Invalid data: %s.' % str(errors), status=400)
    score = score_play(game_id, data)

    place_tiles(game_id, data)
    add_turn_score_and_move(game_id, score,
                            primary_word, secondary_words, data)
    game_continuing = draw_tiles(game_id, data)
    if game_continuing:
        advance_turn(game_id)
    else:
        tally_remaining_tiles(game_id)

    db.session.commit()
    return Response('Turn played successfully.', status=200)


@bp.route('/friends', methods=['GET'])
@login_required
def fetch_friends():
    """Fetch friends and friend key."""
    current_player = db.session.query(Player).filter_by(
        user_id=current_user.id).options(
        subqueryload(Player.friends)).first()
    if current_player is None:
        return Response(
            'Internal server error. Unknown player.', status=400)
    data = {
        'friends': [
            {'player_id': player.id, 'display_name': player.display_name}
            for player in current_player.friends
        ],
        'friend_key': current_player.friend_key
    }
    return jsonify(data)


@bp.route('/add-friend', methods=['POST'])
@login_required
def add_friend():
    """
    Add a friend with the given friend key.

    If player A submits player B's friend key, then player A
    will be added to player B's list of friends and player B
    will also be added to player A's list of friends.
    """
    data = request.get_json()
    if 'friend_key' not in data:
        return Response('No friend key provided.', status=400)
    if len(data) > 1:
        return Response('Too many fields provided.', status=400)
    if len(data['friend_key']) != FRIEND_KEY_LENGTH:
        return Response('Expected a friend key with exactly 15 characters, '
                        'but got %d characters.' % len(data['friend_key']),
                        status=400)
    for character in data['friend_key']:
        if character not in FRIEND_KEY_CHARACTERS:
            return Response('Got unexpected character %s in the '
                            'friend key.' % character, status=400)
    current_player = db.session.query(Player).filter_by(
        user_id=current_user.id).options(subqueryload(Player.friends)).first()
    friend_player = db.session.query(Player).filter_by(
        friend_key=data['friend_key']).options(subqueryload(Player.friends)).first()
    if current_player.id == friend_player.id:
        return Response('You cannot add yourself as a friend.', status=400)
    already_friends = True
    if current_player not in friend_player.friends:
        friend_player.friends.append(current_player)
        already_friends = False
    if friend_player not in current_player.friends:
        current_player.friends.append(friend_player)
        already_friends = False
    if already_friends:
        return Response('You are already friends with %s.' %
                        friend_player.display_name, status=400)
    db.session.commit()
    return Response('Success.', status=200)


@bp.route('/player-settings', methods=['GET', 'POST'])
@login_required
def player_settings():
    """Get/update current settings."""
    player = db.session.query(Player).filter_by(
        user_id=current_user.id).join(Player.dictionary).first()
    if player is None:
        return Response('Internal server error. '
                        'The current player is unknown', status=400)
    if request.method == 'GET':
        data = player.serialize(
            override_mask={
                Player: ['id', 'display_name', 'dictionary', 'friend_key'],
                Dictionary: ['id', 'name']})
        return jsonify(data)
    elif request.method == 'POST':
        data = request.get_json()
        expected_fields = ['display_name', 'dictionary_id', 'friend_key']
        for field in expected_fields:
            if field not in data:
                return Response('Expected \'%s\' in the data.', status=400)
        if len(data) != len(expected_fields):
            return Response('Too many fields sent.', status=400)
    return Response('Unknown method type', status=400)


@bp.route('/new-game', methods=['GET', 'POST'])
@login_required
def new_game():
    """Get new game options or start a new game."""
    if request.method == 'GET':
        current_player = db.session.query(Player).filter_by(
            user_id=current_user.id
        ).options(subqueryload(Player.friends)).first()
        if current_player is None:
            return Response(
                'Internal server error. Unknown player.', status=400)
        data = {
            'friends': [
                {'player_id': player.id, 'display_name': player.display_name}
                for player in current_player.friends
            ]
        }
        return jsonify(data)
    elif request.method == 'POST':
        data = request.get_json()
        if 'friends' not in data or len(data) > 1:
            return Response(
                'Expected exactly one key: \'friends\'.', status=400)
        if len(data['friends']) < 1 or len(data['friends']) > 3:
            return Response(
                'At least one and at most 3 opponents may be chosen.',
                status=400)
        opponent_ids = []
        for friend_data in data['friends']:
            if 'player_id' not in friend_data:
                return Response(
                    'Player ID must be provided for each player.', status=400)
            if friend_data['player_id'] in opponent_ids:
                return Response(
                    'Opponent choices must be distinct.', status=400)
            opponent_ids.append(friend_data['player_id'])
        current_player = db.session.query(Player).filter_by(
            user_id=current_user.id).options(
            joinedload(Player.dictionary)).first()
        if current_player is None:
            return Response(
                'Internal server error. Player is unknown.', status=400)
        opponent_players = db.session.query(Player).filter(
            Player.id.in_(opponent_ids)).all()
        if len(opponent_players) != len(opponent_ids):
            return Response(
                'Internal server error. '
                'Unable to fetch all players.', status=400)
        players = opponent_players + [current_player]
        game_players = [
            GamePlayer(player=player, game=game) for player in players]
        random.shuffle(game_players)
        for index, game_player in enumerate(game_players):
            game_player.turn_order = index
        game = Game(dictionary=current_player.dictionary)
        game.game_player_to_play = game_players[0]
        objects = [game] + game_players
        db.session.add_all(objects)
        db.session.commit()
        initialize_bag(game.id)
        initialize_racks(game.id)
        return Response('New game created!', status=200)
    return Response('Unknown request method.', status=400)


@bp.route('/add-word', methods=['GET', 'POST'])
@login_required
def add_word():
    form = AddWordForm()
    set_dictionary_choices(form)
    if form.validate_on_submit():
        dictionary_id = form.dictionary.data
        word = form.word.data
        lower_word = word.lower()
        definition = form.definition.data
        dictionary = db.session.query(Dictionary).filter(
            Dictionary.id == dictionary_id).options(
            subqueryload(Dictionary.entries)).first()
        if dictionary is None:
            return 'Dictionary %s not found.' % dictionary_id
        entry = db.session.query(Entry).filter(Entry.word == lower_word).first()
        if entry is None:
            new_entry = Entry(word=lower_word, definition=definition)
            db.session.add(new_entry)
            dictionary.entries.append(new_entry)
        else:
            if entry in dictionary.entries:
                return 'The word "%s" is already in this dictionary.' % lower_word
            dictionary.entries.append(entry)
        db.session.commit()
        return 'Successfully added %s to the dictionary.' % lower_word
    return render_template('dictionary/add_word.html', title='Add word', form=form)
