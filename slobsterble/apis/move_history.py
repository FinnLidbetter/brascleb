"""API for viewing the turn history of a game."""

from flask import jsonify, Response
from flask_jwt_extended import jwt_required, current_user
from flask_restful import Resource
from sqlalchemy.orm import joinedload, subqueryload

from slobsterble.app import db
from slobsterble.models import GamePlayer, Move, Player, TileCount, User


class MoveHistoryView(Resource):

    @staticmethod
    @jwt_required()
    def get(game_id):
        """Get the history of turns for a game."""
        moves_query = db.session.query(GamePlayer).filter(
            GamePlayer.game_id == game_id).join(
            GamePlayer.player).join(Player.user).options(
            joinedload(GamePlayer.player),
            subqueryload(GamePlayer.moves).subqueryload(
                Move.exchanged_tiles).joinedload(TileCount.tile))
        if moves_query.count() == 0:
            return Response('No game with ID %d.' % game_id, status=400)
        if moves_query.filter(User.id == current_user.id).count() == 0:
            # The user is not part of this game.
            return Response('User is not authorized.', status=401)
        game_player_moves_list = list(moves_query)
        serialized_moves = []

        def _game_player_sort(game_player):
            return game_player['turn_order']

        def _move_sort(move):
            return move['turn_number']

        def _exchanged_sort(exchanged):
            return exchanged['tile']['letter'] or chr(
                max(ord('z'), ord('Z')) + 1)

        for game_player_moves in game_player_moves_list:
            serialized_game_player_moves = game_player_moves.serialize(
                override_mask={
                    'GamePlayer': ['player', 'moves', 'turn_order'],
                    'Move': ['primary_word', 'secondary_words',
                             'exchanged_tiles', 'turn_number', 'score'],
                    'Player': ['id', 'display_name']
                },
                sort_keys={
                    'GamePlayer': _game_player_sort,
                    'Move': _move_sort,
                    'TileCount': _exchanged_sort
                }
            )
            serialized_moves.append(serialized_game_player_moves)
        return jsonify({'game_players': serialized_moves})
