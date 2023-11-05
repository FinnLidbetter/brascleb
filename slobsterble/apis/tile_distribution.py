"""API for retrieving and updating a user's preferred tile distribution."""

from flask import Response, jsonify, request
from flask_jwt_extended import current_user, jwt_required
from flask_restful import Resource
from jsonschema import ValidationError
from jsonschema import validate as schema_validate
from slobsterble.app import db
from slobsterble.constants import TILE_COUNT_MAX, TILE_VALUE_MAX
from slobsterble.models import Distribution, Player, Tile, TileCount
from slobsterble.utilities.db_utilities import fetch_or_create
from sqlalchemy.orm import joinedload

TILE_DISTRIBUTION_SCHEMA = {
    "type": "array",
    "minItems": 27,
    "maxItems": 27,
    "items": {
        "type": "object",
        "required": ["letter", "value", "count"],
        "properties": {
            "letter": {
                "oneOf": [
                    {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 1,
                        "pattern": "[A-Z]",
                    },
                    {"type": "null"},
                ]
            },
            "value": {
                "type": "integer",
                "minimum": 0,
                "maximum": TILE_VALUE_MAX,
            },
            "count": {
                "type": "integer",
                "minimum": 0,
                "maximum": TILE_COUNT_MAX,
            },
        },
    },
}


class TileDistributionView(Resource):
    @staticmethod
    @jwt_required()
    def get():
        """Get the player's current preferred tile distribution."""
        player = (
            db.session.query(Player)
            .filter_by(user_id=current_user.user_id)
            .options(
                joinedload(Player.distribution)
                .subqueryload(Distribution.tile_distribution)
                .joinedload(TileCount.tile)
            )
            .one()
        )

        def _letter_sort(tile):
            return tile["letter"] or chr(max(ord("Z"), ord("z")) + 1)

        serialized_data = player.serialize(
            override_mask={
                "Player": ["distribution"],
                "Distribution": ["name", "tile_distribution"],
                "TileCount": ["tile", "count"],
                "Tile": ["letter", "value", "is_blank"],
            },
            sort_keys={"Tile": _letter_sort},
        )
        return jsonify(serialized_data["distribution"])

    @staticmethod
    @jwt_required()
    def post():
        """Update the player's current preferred tile distribution."""
        data = request.get_json()
        try:
            schema_validate(data, TILE_DISTRIBUTION_SCHEMA)
        except ValidationError:
            return Response("Data does not conform to the schema.", status=400)
        letter_set = {tile_count.letter for tile_count in data}
        if len(letter_set) != len(data):
            return Response("Duplicate letters included in the data.", status=400)
        player = (
            db.session.query(Player)
            .filter_by(user_id=current_user.id)
            .joinedload(Player.distribution)
            .one()
        )
        distribution = (
            db.session.query(Distribution)
            .filter_by(name=data["name"], creator_id=player.id)
            .one_or_none()
        )
        is_new_distribution = distribution is None
        if is_new_distribution:
            distribution = Distribution(name=data["name"], creator_id=player.id)
        tile_counts = []
        for data_tile in data:
            tile = fetch_or_create(
                db.session,
                Tile,
                letter=data_tile["letter"],
                value=data_tile["value"],
                is_blank=data_tile["letter"] is None,
            )
            tile_count = fetch_or_create(
                db.session, TileCount, tile_id=tile.id, count=data_tile["count"]
            )
            tile_counts.append(tile_count)
        distribution.tile_distribution = tile_counts
        if is_new_distribution:
            db.session.add(distribution)
        player.distribution = distribution
        db.session.commit()
        return Response("Successfully updated the tile distribution.")
