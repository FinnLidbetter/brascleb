"""API for checking words in the dictionary."""

from collections import defaultdict

from flask import jsonify, request, Response
from flask_jwt_extended import jwt_required, current_user
from flask_restful import Resource
from sqlalchemy.sql.expression import func

from slobsterble.app import db
from slobsterble.models import Dictionary, Entry, Game, GamePlayer, Player


class TwoLetterWordView(Resource):
    """Get a list of two letter words."""

    two_letter_words = defaultdict(list)

    @classmethod
    @jwt_required()
    def get(cls, game_id):
        """Get a list of all two letter words for the dictionary in a game."""
        refresh = request.args.get('refresh')
        accessible_game = db.session.query(Game).filter(
            Game.id == game_id
        ).join(
            Game.game_players,
            GamePlayer.player,
        ).filter(Player.user_id == current_user.id).one_or_none()
        if not accessible_game:
            return Response(status=401)
        dictionary_id = accessible_game.dictionary_id
        if dictionary_id in cls.two_letter_words and not refresh:
            return jsonify(cls.two_letter_words[dictionary_id])
        query = db.session.query(Dictionary, Entry).filter(
            Dictionary.id == dictionary_id
        ).join(
            Dictionary.entries
        ).filter(
            func.length(Entry.word) == 2
        ).order_by(
            Entry.word
        )
        two_letter_words = query.all()
        words = [row[1].word for row in two_letter_words]
        cls.two_letter_words[dictionary_id] = words
        return jsonify(words)


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
