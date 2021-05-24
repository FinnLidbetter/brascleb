"""API views."""
import random

from flask import Blueprint, Response, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload, subqueryload

from slobsterble.app import db
from slobsterble.constants import (
    ACTIVE_GAME_LIMIT,
    DISPLAY_NAME_LENGTH_MAX,
    FRIEND_KEY_CHARACTERS,
    FRIEND_KEY_LENGTH,
    GAME_PLAYERS_MAX)
from slobsterble.forms import (
    AddWordForm,
    set_dictionary_choices,
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
    set_completed_time,
    tally_remaining_tiles,
    validate_plausible_data,
    validate_play,
    validate_play_data,
    validate_user_turn,
)
from slobsterble.models import (
    BoardLayout,
    Dictionary,
    Distribution,
    Entry,
    Game,
    GamePlayer,
    Modifier,
    Move,
    PlayedTile,
    Player,
    PositionedModifier,
    Role,
    Tile,
    TileCount,
    User,
)
from slobsterble.game_play_views import bp as game_blueprint


bp = Blueprint('api', __name__, url_prefix='/api')
bp.register_blueprint(game_blueprint)


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


@bp.route('/player-settings', methods=['GET', 'POST'])
@login_required
def player_settings():
    """Get/update current settings."""
    # player = db.session.query(Player).filter_by(
    #     user_id=current_user.id).join(Player.dictionary).first()
    player = db.session.query(Player).join(Player.user).filter(User.id == current_user.id).first()
    if player is None:
        return Response('Internal server error. '
                        'The current player is unknown', status=400)
    if request.method == 'GET':
        player_data = player.serialize(
            override_mask={
                Player: ['display_name', 'dictionary', 'friend_key'],
                Dictionary: ['id', 'name']})
        dictionaries = db.session.query(Dictionary).all()
        dictionaries_data = []
        for dictionary in dictionaries:
            dictionaries_data.append(
                dictionary.serialize(override_mask={Dictionary: ['id', 'name']}))
        data = {'player': player_data,
                'dictionaries': dictionaries_data}
        return jsonify(data)
    elif request.method == 'POST':
        data = request.get_json()
        expected_top_fields = ['display_name', 'dictionary', 'friend_key']
        for field in expected_top_fields:
            if field not in data:
                return Response('Expected \'%s\' in the data.', status=400)
        if len(data) != len(expected_top_fields):
            return Response('Too many fields sent.', status=400)
        if 'id' not in data['dictionary'] or 'name' not in data['dictionary']:
            return Response('Missing field in the dictionary.', status=400)
        if len(data['dictionary']) != 2:
            return Response('Too many fields sent.', status=400)
        if len(data['friend_key']) != FRIEND_KEY_LENGTH:
            return Response('Expected a friend key with exactly 15 characters, '
                            'but got %d characters.' % len(data['friend_key']),
                            status=400)
        for character in data['friend_key']:
            if character not in FRIEND_KEY_CHARACTERS:
                return Response('Got unexpected character %s in the '
                                'friend key.' % character, status=400)
        if data['friend_key'] != player.friend_key:
            player.friend_key = data['friend_key']
        if data['dictionary']['id'] != player.dictionary.id:
            chosen_dictionary = db.session.query(Dictionary).filter_by(
                id=data['dictionary']['id']).first()
            if chosen_dictionary is None:
                return Response(
                    'Internal server error. Dictionary not found.', status=400)
            player.dictionary = chosen_dictionary
        if data['display_name'] != player.display_name:
            if len(data['display_name']) > DISPLAY_NAME_LENGTH_MAX:
                return Response(
                    'Chosen display name is too long.', status=400)
            player.display_name = data['display_name']
        db.session.commit()
        return Response('Success!', status=200)
    return Response('Unknown method type', status=400)
