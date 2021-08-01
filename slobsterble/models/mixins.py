from datetime import datetime

from sqlalchemy import func
from sqlalchemy.inspection import inspect

from slobsterble.app import db


class MetadataMixin:
    """Add common metadata fields to the model."""
    created = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc='The date and time that the model first created.')
    modified = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        onupdate=func.now(),
        doc='The date and time that the model was last modified.')


class IDPKMixin:
    """Mixin for adding an integer ID."""
    id = db.Column(db.Integer,
                   primary_key=True,
                   autoincrement=True,
                   doc='Integer ID for the model instance.')


class ModelMixin(IDPKMixin, MetadataMixin):
    """Mixin with all common fields."""


class ModelSerializer:
    """Base model serializer mixin."""
    # Exclude these fields from all models.
    base_exclude_fields = ['id', 'created', 'modified']
    serialize_exclude_fields = []

    # Use serialize_include_fields to override base exclusions.
    serialize_include_fields = []

    def serialize_type(self, obj, exclusions=None, override_mask=None, sort_keys=None):
        """Recursively serialize according to type."""
        if getattr(obj, 'serialize', None):
            result = obj.serialize(exclusions, override_mask, sort_keys)
            return result
        elif isinstance(obj, list):
            result = self.serialize_list(obj, exclusions, override_mask, sort_keys)
            return result
        elif isinstance(obj, datetime):
            return int(obj.timestamp())
        elif isinstance(obj, (bool, int)):
            return obj
        elif obj is None:
            return None
        return str(obj)

    def serialize(self, exclusions=None, override_mask=None, sort_keys=None):
        """Serialize model fields recursively subject to exclusions."""
        result = {}
        if override_mask is not None and type(self).__name__ in override_mask:
            for column in override_mask[type(self).__name__]:
                serialized = self.serialize_type(getattr(self, column),
                                                 exclusions,
                                                 override_mask,
                                                 sort_keys)
                result[column] = serialized
            return result
        model_columns = inspect(self).attrs.keys()
        for column in model_columns:
            if column in self.base_exclude_fields and \
                    column not in self.serialize_include_fields:
                continue
            if column in self.serialize_exclude_fields:
                continue
            if exclusions is not None and type(self).__name__ in exclusions \
                    and column in exclusions[type(self).__name__]:
                continue
            serialized = self.serialize_type(
                getattr(self, column), exclusions, override_mask, sort_keys)
            result[column] = serialized

        return result

    @staticmethod
    def serialize_list(items, exclusions=None, override_mask=None, sort_keys=None):
        """Serialize a list of objects."""
        serialized_list = [item.serialize(exclusions, override_mask, sort_keys)
                           for item in items]
        if sort_keys is not None and serialized_list and type(items[0]).__name__ in sort_keys:
            serialized_list.sort(key=sort_keys[type(items[0]).__name__])
        return serialized_list
