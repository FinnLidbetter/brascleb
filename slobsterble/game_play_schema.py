"""JSON schema for played turns."""

from slobsterble.constants import (
    GAME_COLUMNS_MAX,
    GAME_ROWS_MAX,
    TILE_VALUE_MAX,
    TILES_ON_RACK_MAX,
)


def _schema_played_tile():
    """JSON schema for a tile played on a board."""
    return {
        'type': 'object',
        'required': ['row', 'column', 'letter', 'value',
                     'is_blank', 'is_exchange'],
        'properties': {
            'row': {
                'type': 'integer',
                'minimum': 0,
                'maximum': GAME_ROWS_MAX,
            },
            'column': {
                'type': 'integer',
                'minimum': 0,
                'maximum': GAME_COLUMNS_MAX,
            },
            'letter': {
                'type': 'string',
                'maxLength': 1,
                'minLength': 1,
                'pattern': '[A-Z]',
            },
            'value': {
                'type': 'integer',
                'minimum': 0,
                'maximum': TILE_VALUE_MAX,
            },
            'is_blank': {
                'type': 'boolean',
            },
            'is_exchange': {
                'const': False
            }
        }
    }


def _schema_exchanged_blank():
    """JSON schema for an exchanged blank tile."""
    return {
        'type': 'object',
        'required': ['row', 'column', 'letter', 'value',
                     'is_blank', 'is_exchange'],
        'properties': {
            'row': {
                'type': 'null',
            },
            'column': {
                'type': 'null',
            },
            'letter': {
                'type': 'null',
            },
            'value': {
                'type': 'integer',
                'minimum': 0,
                'maximum': TILE_VALUE_MAX,
            },
            'is_blank': {
                'const': True,
            },
            'is_exchange': {
                'const': True,
            }
        }
    }


def _schema_exchanged_letter():
    """JSON schema for an exchanged letter tile."""
    return {
        'type': 'object',
        'required': ['row', 'column', 'letter', 'value',
                     'is_blank', 'is_exchange'],
        'properties': {
            'row': {
                'type': 'null',
            },
            'column': {
                'type': 'null',
            },
            'letter': {
                'type': 'string',
                'maxLength': 1,
                'minLength': 1,
                'pattern': '[A-Z]',
            },
            'value': {
                'type': 'integer',
                'minimum': 0,
                'maximum': TILE_VALUE_MAX,
            },
            'is_blank': {
                'const': False,
            },
            'is_exchange': {
                'const': True,
            }
        }
    }


def _schema_exchanged_tile():
    """JSON schema for an exchanged tile."""
    return {
        'oneOf': [
            _schema_exchanged_blank(),
            _schema_exchanged_letter(),
        ]
    }


# JSON schema for a turn.
TURN_PLAY_SCHEMA = {
    'anyOf': [
        {
            'type': 'array',
            'minItems': 0,
            'maxItems': TILES_ON_RACK_MAX,
            'items': _schema_played_tile(),
        },
        {
            'type': 'array',
            'minItems': 0,
            'maxItems': TILES_ON_RACK_MAX,
            'items': _schema_exchanged_tile(),
        },
    ]
}
