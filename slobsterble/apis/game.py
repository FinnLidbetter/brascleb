"""Views related to game play."""

import sqlalchemy.orm.exc
from flask import Response, request, g, jsonify
from flask_restful import Resource
from flask_jwt_extended import jwt_required, current_user
from sqlalchemy.orm import subqueryload, joinedload

import slobsterble.play_exceptions
from slobsterble.app import db
from slobsterble.game_play_controller import (
    StatelessValidator,
    StatefulValidator,
    StateUpdater,
    WordBuilder,
    WordValidator,
    fetch_game_state,
    get_game_player,
)
from slobsterble.models import (GamePlayer, Move, TileCount, Player, User)


class GameView(Resource):

    @staticmethod
    @jwt_required()
    def get(game_id):
        """
        Get the current state of the game.

        This includes:
        - The played tiles.
        - The names and scores of the other players.
        - The logged in user's rack tiles.
        - The number of tiles remaining.
        - Whose turn it is.
        """
        try:
            game_state = fetch_game_state(game_id)
        except sqlalchemy.orm.exc.NoResultFound:
            return Response(
                'Game with id %s not found.' % str(game_id), status=404)
        if not any(game_player.player.user_id == g.user.id
                   for game_player in game_state.game_players):
            return Response('User is not authorized to access this game.',
                            status=401)
        serialized_game_state = game_state.serialize(
            override_mask={'Game': ['board_state', 'game_players',
                                    'whose_turn_name', 'num_tiles_remaining',
                                    'board_layout'],
                           'GamePlayer': ['score', 'player'],
                           'Player': ['id', 'display_name'],
                           'PlayedTile': ['tile', 'row', 'column'],
                           'Tile': ['letter', 'is_blank', 'value'],
                           'BoardLayout': ['rows', 'columns', 'modifiers'],
                           'PositionedModifier': ['row', 'column', 'modifier'],
                           'Modifier': ['letter_multiplier', 'word_multiplier']})
        current_game_player = None
        for game_player in game_state.game_players:
            if game_player.player.user_id == g.user.id:
                current_game_player = game_player
                break
        serialized_user_rack = current_game_player.serialize(
            override_mask={'GamePlayer': ['rack'],
                           'TileCount': ['tile', 'count'],
                           'Tile': ['letter', 'is_blank', 'value']})
        serialized_game_state['rack'] = serialized_user_rack['rack']
        return jsonify(serialized_game_state)

    @staticmethod
    @jwt_required()
    def post(game_id):
        """API to play a turn of the game."""
        data = request.get_json()
        try:
            stateless_validator = StatelessValidator(data)
            stateless_validator.validate()
            game_state = fetch_game_state(game_id)
            game_player = get_game_player(game_state)
            stateful_validator = StatefulValidator(data, game_state, game_player)
            stateful_validator.validate()
            game_board = stateful_validator.game_board
            word_builder = WordBuilder(data, game_board)
            primary_word, secondary_words = word_builder.get_played_words()
            score = word_builder.compute_score()
            if primary_word is not None:
                word_validator = WordValidator([primary_word] + secondary_words,
                                               game_state.dictionary_id)
                word_validator.validate()
            state_updater = StateUpdater(
                data=data, game_state=game_state, game_player=game_player,
                score=score, primary_word=primary_word,
                secondary_words=secondary_words)
            state_updater.update_state()
            return Response('Turn played successfully.', status=200)
        except slobsterble.play_exceptions.BasePlayException as play_error:
            return Response(str(play_error), status=play_error.status_code)
        except sqlalchemy.orm.exc.NoResultFound:
            return Response('Game does not exist.', status=400)


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
