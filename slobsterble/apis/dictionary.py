"""API for checking words in the dictionary."""

from flask import jsonify, Response
from flask_jwt_extended import jwt_required, current_user
from flask_restful import Resource

from slobsterble.app import db
from slobsterble.models import Dictionary, Entry, Game, GamePlayer, Player


class DictionaryView(Resource):

    @staticmethod
    @jwt_required()
    def get(game_id, word):
        """Check if a word is in the dictionary."""
        has_game_access = db.session.query(Game).filter(
            Game.id == game_id
        ).join(
            Game.game_players,
            GamePlayer.player
        ).filter(Player.user_id == current_user.id).one_or_none()
        if not has_game_access:
            return Response(status=401)

        game_entry_tuple = db.session.query(Game, Entry).filter(
            Game.id == game_id
        ).join(
            Game.dictionary,
            Dictionary.entries
        ).filter(
            Entry.word == word
        ).first()
        if game_entry_tuple is None:
            return jsonify({'word': None, 'definition': None})
        game, entry = game_entry_tuple

        return jsonify(entry.serialize())
