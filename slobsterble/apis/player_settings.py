"""API for retrieving and updating player settings."""

from flask import jsonify, request, Response
from flask_jwt_extended import jwt_required, current_user
from flask_restful import Resource
from jsonschema import validate as schema_validate, ValidationError

from slobsterble.app import db
from slobsterble.constants import (
    DISPLAY_NAME_LENGTH_MAX,
    FRIEND_KEY_CHARACTERS,
    FRIEND_KEY_LENGTH,
)
from slobsterble.models import Player, Dictionary


PLAYER_SETTINGS_SCHEMA = {
    "type": "object",
    "required": ["display_name", "dictionary", "friend_key"],
    "properties": {
        "display_name": {
            "type": "string",
            "minLength": 1,
            "maxLength": DISPLAY_NAME_LENGTH_MAX,
            "pattern": "[A-Za-z0-9 ]+",
        },
        "dictionary": {
            "type": "object",
            "required": ["id", "name"],
            "properties": {
                "id": {
                    "type": "integer",
                },
                "name": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 30,
                    "pattern": "[A-Za-z0-9 ]+",
                },
            },
        },
        "friend_key": {
            "type": "string",
            "minLength": FRIEND_KEY_LENGTH,
            "maxLength": FRIEND_KEY_LENGTH,
            "pattern": "[" + FRIEND_KEY_CHARACTERS + "]+",
        },
    },
}


class PlayerSettingsView(Resource):
    @staticmethod
    @jwt_required()
    def get():
        """Get the player's current settings."""
        player = db.session.query(Player).filter_by(user_id=current_user.id).one()
        player_data = player.serialize(
            override_mask={
                "Player": [
                    "display_name",
                    "dictionary",
                    "friend_key",
                    "distribution",
                    "board_layout",
                ],
                "Dictionary": ["id", "name"],
                "Distribution": ["id", "name"],
                "BoardLayout": ["id", "name"],
            }
        )
        dictionaries = db.session.query(Dictionary).all()
        dictionaries_data = []
        for dictionary in dictionaries:
            dictionaries_data.append(
                dictionary.serialize(override_mask={"Dictionary": ["id", "name"]})
            )
        data = {"player": player_data, "dictionaries": dictionaries_data}
        return jsonify(data)

    @staticmethod
    @jwt_required()
    def post():
        """Update the player's current settings."""
        data = request.get_json()
        try:
            schema_validate(data, PLAYER_SETTINGS_SCHEMA)
        except ValidationError:
            return Response("Data does not conform to the schema.", status=400)
        player = db.session.query(Player).filter_by(user_id=current_user.id).one()
        player.friend_key = data["friend_key"]
        if data["dictionary"]["id"] != player.dictionary.id:
            chosen_dictionary = (
                db.session.query(Dictionary)
                .filter_by(id=data["dictionary"]["id"])
                .one_or_none()
            )
            if chosen_dictionary is None:
                return Response(
                    "Internal server error. Dictionary not found.", status=400
                )
            player.dictionary = chosen_dictionary
        if data["display_name"] != player.display_name:
            player.display_name = data["display_name"]
        db.session.commit()
        return Response("Success!", status=200)
