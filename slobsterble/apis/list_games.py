"""API for listing active games."""

from flask import jsonify, request
from flask_jwt_extended import current_user, jwt_required
from flask_restful import Resource
from slobsterble.app import db
from slobsterble.constants import ACTIVE_GAME_LIMIT
from slobsterble.models import Game, GamePlayer, Player
from sqlalchemy import case


class ListGamesView(Resource):
    @jwt_required()
    def get(self):
        """
        Get a summary of recently started/completed games.

        Return at most ACTIVE_GAME_LIMIT rows. The returned games are sorted by
        completed (incomplete first) first, and the time that the game was
        started (more recent, first) second.
        """
        if request.headers.get("Accept-version") == "v2":
            return self._get_version_2()
        else:
            return self._get_version_1()

    @staticmethod
    def _get_version_1():
        user_games = (
            db.session.query(Game)
            .join(Game.game_players)
            .join(GamePlayer.player)
            .filter(Player.user_id == current_user.id)
            .order_by(
                case([(Game.completed.is_(None), 0)], else_=1),
                Game.completed.desc(),
                Game.started.desc(),
            )
            .limit(ACTIVE_GAME_LIMIT)
            .all()
        )

        def _game_player_sort(game_player):
            return game_player["turn_order"]

        def _game_sort(game):
            return game["completed"] or 0, game["started"]

        serialized_games = Game.serialize_list(
            user_games,
            override_mask={
                "Game": [
                    "started",
                    "completed",
                    "whose_turn_name",
                    "game_players",
                    "id",
                ],
                "GamePlayer": ["score", "player", "turn_order"],
                "Player": ["display_name", "id"],
            },
            sort_keys={"Game": _game_sort, "GamePlayer": _game_player_sort},
        )
        return jsonify(serialized_games)

    @staticmethod
    def _get_version_2():
        user_games = (
            db.session.query(Game)
            .join(Game.game_players)
            .join(GamePlayer.player)
            .filter(Player.user_id == current_user.id)
            .order_by(
                case([(Game.completed.is_(None), 0)], else_=1),
                Game.completed.desc(),
                Game.started.desc(),
            )
            .limit(ACTIVE_GAME_LIMIT)
            .all()
        )

        def _game_player_sort(game_player):
            return game_player["turn_order"]

        def _game_sort(game):
            return game["completed"] or 0, game["started"]

        serialized_games = Game.serialize_list(
            user_games,
            override_mask={
                "Game": ["started", "completed", "whose_turn", "game_players", "id"],
                "GamePlayer": ["score", "player", "turn_order"],
                "Player": ["display_name", "id"],
            },
            sort_keys={"Game": _game_sort, "GamePlayer": _game_player_sort},
        )
        requesting_player = (
            db.session.query(Player).filter_by(user_id=current_user.id).one()
        )
        result = {
            "games": serialized_games,
            "requester": requesting_player.serialize(
                override_mask={"Player": ["display_name", "id"]}
            ),
        }
        return jsonify(result)
