"""API view for getting and adding friends."""

from flask import jsonify, Response
from flask_jwt_extended import jwt_required, current_user
from flask_restful import Resource

from slobsterble.app import db
from slobsterble.models import Player


class StatsView(Resource):

    @staticmethod
    @jwt_required()
    def get():
        """Get the current user's friend key and their friends."""
        current_player = db.session.query(Player).filter_by(
            user_id=current_user.id).one_or_none()
        if current_player is None:
            return Response(status=401)
        data = {
            'wins': current_player.wins,
            'losses': current_player.losses,
            'ties': current_player.ties,
            'best_individual_game_score': current_player.highest_individual_score,
            'best_combined_game_score': current_player.highest_combined_score,
            'best_word_score': current_player.best_word_score,
        }
        return jsonify(data)
