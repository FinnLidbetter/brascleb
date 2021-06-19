"""Utility functions for working with the database generally."""

from sqlalchemy.exc import SQLAlchemyError


def fetch_or_create(session, model, **kwargs):
    """Fetch an instance of the model with the given parameters."""
    instance = session.query(model).filter_by(**kwargs).one_or_none()
    if instance is not None:
        return instance, False
    instance = model(**kwargs)
    try:
        session.add(instance)
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        instance = session.query(model).filter_by(**kwargs).one()
        return instance, False
    return instance, True
