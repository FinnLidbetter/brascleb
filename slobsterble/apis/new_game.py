"""API for creating a new game."""

from flask import jsonify, request, Response
from flask_jwt_extended import jwt_required, current_user
from flask_restful import Resource
from sqlalchemy.orm import subqueryload

from slobsterble.app import db
from slobsterble.game_setup_controller import (
    StatelessValidator,
    StatefulValidator,
    StateUpdater,
)
from slobsterble.models import Player
from slobsterble.api_exceptions import BaseApiException


class NewGameView(Resource):

    @staticmethod
    @jwt_required()
    def get():
        current_player = db.session.query(Player).filter(
            Player.user_id == current_user.id).options(
            subqueryload(Player.friends)).one()
        data = {
            'friends': [
                {
                    'player_id': player.id,
                    'display_name': player.display_name}
                for player in current_player.friends
            ]
        }
        return jsonify(data)

    @staticmethod
    @jwt_required()
    def post():
        """Start a new game."""
        data = request.get_json()
        try:
            stateless_validator = StatelessValidator(data)
            stateless_validator.validate()
            player = db.session.query(Player).filter_by(
                user_id=current_user.id
            ).options(subqueryload(Player.friends)).one()
            stateful_validator = StatefulValidator(data, player)
            stateful_validator.validate()
            state_updater = StateUpdater(data, player)
            state_updater.update_state()
            return Response('New game created successfully.', status=200)
        except BaseApiException as new_game_error:
            return Response(
                str(new_game_error), status=new_game_error.status_code)
