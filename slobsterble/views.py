"""API views."""
import json
import random

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload, subqueryload

from slobsterble import db
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
    mutate_data,
    place_tiles,
    score_play,
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

ACTIVE_GAME_LIMIT = 10
RACK_TILES_MAX = 7

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/active-games', methods=['GET'])
@login_required
def get_active_games():
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
        override_mask={Game: ['started', 'whose_turn_name', 'game_players', 'id'],
                       GamePlayer: ['score', 'player'],
                       Player: ['display_name']})
    return jsonify(games=serialized_games)


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
        # TODO: return HTTP status code.
        print('Game does not exist')
        return {}
    if game_query.filter(User.id == current_user.id).count() == 0:
        # The user is not part of this game.
        # TODO: return HTTP status code.
        print('User is not authorized')
        return {}
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
    return jsonify(game_state=serialized_game_state)


@bp.route('/game/<int:game_id>/verify-word/<string:word>', methods=['GET'])
@login_required
def verify_word(game_id, word):
    game_query = db.session.query(Game).filter(Game.id == game_id).join(
        Game.game_players).join(GamePlayer.player).join(Player.user)
    if game_query.count() == 0:
        # The game does not exist.
        # TODO: return HTTP status code.
        print('Game does not exist')
        return {}
    if game_query.filter(User.id == current_user.id).count() == 0:
        # The user is not part of this game.
        # TODO: return HTTP status code.
        print('User is not authorized')
        return {}
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
    form = TemporaryPlayForm()
    new_tiles = []
    game_completed = False
    if form.validate_on_submit():
        json_str = form.played_tiles_json.data
        data = json.loads(json_str)
    # data = request.json
        is_valid_data = validate_play_data(data)
        if not is_valid_data:
            return 'Invalid data.'
        mutate_data(data)
        is_plausible_data = validate_plausible_data(data)
        is_current_user_turn = validate_user_turn(current_user, game_id)
        if not is_current_user_turn:
            return 'It is not your turn.'
        valid_play, info = validate_play(game_id, data)
        if not valid_play:
            return info
        primary_word = info[0]
        secondary_words = info[1:]
        score = score_play(game_id, data)

        place_tiles(game_id, data)
        add_turn_score_and_move(game_id, score,
                                primary_word, secondary_words, data)
        game_continuing = draw_tiles(game_id, data)
        if game_continuing:
            advance_turn(game_id)
        else:
            tally_remaining_tiles(game_id, data)
            
        db.session.commit()
        return 'Turn played successfully.'
    return render_template('game/play_turn.html', title='Play turn', form=form)

@bp.route('/new-game', methods=['GET', 'POST'])
@login_required
def new_game():
    form = NewGameForm()
    set_opponent_choices(current_user.id, form)
    set_dictionary_choices(form)
    if form.validate_on_submit():
        dictionary_id = form.dictionary.data
        opponent_player_ids = form.opponents.data
        dictionary = db.session.query(Dictionary).filter(
            Dictionary.id == dictionary_id).first()
        game = Game(dictionary=dictionary)
        opponent_players = db.session.query(Player).filter(
            Player.id.in_(opponent_player_ids)).all()
        current_player = db.session.query(Player).join(Player.user).filter(
            User.id == current_user.id).first()
        players = opponent_players + [current_player]
        game_players = [
            GamePlayer(player=player, game=game) for player in players]
        random.shuffle(game_players)
        for index, game_player in enumerate(game_players):
            game_player.turn_order = index
        game.game_player_to_play = game_players[0]
        objects = [game] + game_players
        db.session.add_all(objects)
        db.session.commit()
        initialize_bag(game.id)
        initialize_racks(game.id)
        return 'New game started.'
    return render_template('game/new_game.html', title='New game', form=form)

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
