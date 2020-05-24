"""API views."""

from flask import Blueprint, jsonify
from flask_login import current_user, login_required
from sqlalchemy.orm import subqueryload

from slobsterble import db
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

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/active_games', methods=['GET'])
@login_required
def get_active_games():
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
        override_mask={Game: ['started', 'whose_turn', 'game_players'],
                       GamePlayer: ['score', 'player'],
                       Player: ['display_name']})
    return jsonify(games=serialized_games)
