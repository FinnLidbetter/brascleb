"""API for setting a user's preferred Board Layout."""

from flask import jsonify, request, Response
from flask_jwt_extended import jwt_required, current_user
from flask_restful import Resource
from jsonschema import validate as schema_validate, ValidationError
from sqlalchemy.orm import joinedload

from slobsterble.app import db
from slobsterble.constants import (
    GAME_COLUMNS_MIN,
    GAME_COLUMNS_MAX,
    GAME_ROWS_MIN,
    GAME_ROWS_MAX,
    MULTIPLIER_MIN,
    MULTIPLIER_MAX,
)
from slobsterble.models import BoardLayout, Modifier, Player, PositionedModifier
from slobsterble.utilities.db_utilities import fetch_or_create


BOARD_LAYOUT_SCHEMA = {
    "type": "object",
    "required": ["name", "rows", "columns", "layout"],
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 30,
            "pattern": "[A-Za-z0-9 ]+",
        },
        "rows": {
            "type": "integer",
            "minimum": GAME_ROWS_MIN,
            "maximum": GAME_ROWS_MAX,
        },
        "columns": {
            "type": "integer",
            "minimum": GAME_COLUMNS_MIN,
            "maximum": GAME_COLUMNS_MAX,
        },
        "layout": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["row", "column", "letter_multiplier", "word_multiplier"],
                "properties": {
                    "row": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": GAME_ROWS_MAX - 1,
                    },
                    "column": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": GAME_COLUMNS_MAX - 1,
                    },
                    "letter_multiplier": {
                        "type": "integer",
                        "minimum": MULTIPLIER_MIN,
                        "maximum": MULTIPLIER_MAX,
                    },
                    "word_multiplier": {
                        "type": "integer",
                        "minimum": MULTIPLIER_MIN,
                        "maximum": MULTIPLIER_MAX,
                    },
                },
            },
        },
    },
}


class BoardLayoutView(Resource):
    @staticmethod
    @jwt_required()
    def get():
        """Get the player's current board layout."""
        player = (
            db.session.query(Player)
            .filter_by(user_id=current_user.id)
            .options(
                joinedload(Player.board_layout)
                .subqueryload(BoardLayout.modifiers)
                .joinedload(PositionedModifier.modifier)
            )
            .one()
        )
        serialized_data = player.serialize(
            override_mask={
                "Player": ["board_layout"],
                "BoardLayout": ["name", "rows", "columns", "modifiers"],
                "PositionedModifier": ["row", "column", "modifier"],
                "Modifier": ["letter_multiplier", "word_multiplier"],
            }
        )
        return jsonify(serialized_data["board_layout"])

    @staticmethod
    @jwt_required()
    def post():
        """Update the player's board layout."""
        data = request.get_json()
        try:
            schema_validate(data, BOARD_LAYOUT_SCHEMA)
        except ValidationError:
            return Response("Data does not conform to the schema.", status=400)
        if data["rows"] % 2 != 1:
            return Response("Number of rows must be odd.", status=400)
        if data["columns"] % 2 != 1:
            return Response("Number of columns must be odd.", status=400)
        positions = {
            (modifier["row"], modifier["column"]) for modifier in data["layout"]
        }
        if len(positions) != len(data["layout"]):
            return Response(
                "Multiple modifiers given for the same row and column.", status=400
            )
        player = (
            db.session.query(Player)
            .filter_by(user_id=current_user.id)
            .joinedload(Player.board_layout)
            .one()
        )
        board_layout = (
            db.session.query(BoardLayout)
            .filter_by(name=data["name"], creator_id=player.id)
            .one_or_none()
        )
        is_new_layout = board_layout is not None
        if board_layout is None:
            board_layout = BoardLayout(
                name=data["name"], rows=data["rows"], columns=data["columns"]
            )
        modifiers = []
        for modifier_data in data["layout"]:
            modifier = fetch_or_create(
                db.session,
                Modifier,
                letter_multiplier=modifier_data["letter_multiplier"],
                word_multiplier=modifier_data["word_multiplier"],
            )
            positioned_modifier = fetch_or_create(
                db.session,
                PositionedModifier,
                modifier_id=modifier.id,
                row=modifier_data["row"],
                column=modifier_data["column"],
            )
            modifiers.append(positioned_modifier)
        board_layout.modifiers = modifiers
        if is_new_layout:
            db.session.add(board_layout)
        player.board_layout = board_layout
        db.session.commit()
