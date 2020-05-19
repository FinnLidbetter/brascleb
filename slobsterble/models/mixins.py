from sqlalchemy import func

from slobsterble import db


class MetadataMixin:
    """Add common metadata fields to the model."""
    created = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        doc='The date and time that the model first created.')
    modified = db.Column(
        db.DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        doc='The date and time that the model was last modified.')


class IDPKMixin:
    """Mixin for adding an integer ID."""
    id = db.Column(db.Integer,
                   primary_key=True,
                   doc='Integer ID for the model instance.')


class ModelMixin(IDPKMixin, MetadataMixin):
    """Mixin with all common fields."""
