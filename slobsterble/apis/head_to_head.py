"""API view for getting head-to-head stats."""

from flask import jsonify
from flask_jwt_extended import jwt_required, current_user
from flask_restful import Resource

from slobsterble.app import db
from slobsterble.models import GamePlayer


class HeadToHeadView(Resource):
    @staticmethod
    @jwt_required()
    def get(other_player_id):
        """Get the current user's friend key and their friends."""
        game_players = (
            db.session.query(GamePlayer)
            .join(GamePlayer.player)
            .filter_by(user_id=current_user.id)
            .join(GamePlayer.game)
            .all()
        )
        wins = 0
        ties = 0
        losses = 0
        best_combined = 0
        for game_player in game_players:
            game = game_player.game
            if not game.completed:
                continue
            is_head_to_head = False
            combined_score = 0
            for game_game_player in game.game_players:
                if game_game_player.player_id == other_player_id:
                    is_head_to_head = True
                    other_game_player = game_game_player
                    if game_player.score > other_game_player.score:
                        wins += 1
                    elif game_player.score < other_game_player.score:
                        losses += 1
                    else:
                        ties += 1
                combined_score += game_game_player.score
            if is_head_to_head and combined_score > best_combined:
                best_combined = combined_score
        data = {
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "best_combined_game_score": best_combined,
        }
        return jsonify(data)
