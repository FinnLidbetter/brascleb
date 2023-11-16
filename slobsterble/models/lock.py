"""
Model for a simple locking mechanism.

At the current scale, using a database locking mechanism is
acceptable. It should be replaced with a queueing mechanism
in the future if performance problems arise.
"""
import datetime
import time
from contextlib import contextmanager

import sqlalchemy.exc
from slobsterble.app import db
from slobsterble.models.mixins import ModelMixin


class Lock(db.Model, ModelMixin):
    """A utility table for a locking mechanism."""

    key = db.Column(
        db.String(256),
        nullable=False,
        unique=True,
        doc="A unique identifying string for the lock.",
    )
    expiry = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        doc="The datetime after which the lock is invalid and should be "
        "ignored and deleted.",
    )


@contextmanager
def acquire_lock(key, expire_seconds=60, block_seconds=None):
    """Get a lock with the given key and expiry after optionally blocking."""
    lock_acquired = False
    try:
        first_check = True
        start_time = time.time()
        if block_seconds is None:
            block_seconds = -1
        while (
            time.time() < start_time + block_seconds or first_check
        ) and not lock_acquired:
            first_check = False
            lock = db.session.query(Lock).filter_by(key=key).one_or_none()
            if lock is None:
                lock = Lock(
                    key=key,
                    expiry=datetime.datetime.now()
                    + datetime.timedelta(seconds=expire_seconds),
                )
                lock_acquired = True
                db.session.add(lock)
            else:
                if lock.expiry < datetime.datetime.now():
                    # This lock should not still be here. It can be deleted.
                    # But rather than deleting and recreating it, just update
                    # the expiration.
                    lock.expiry = datetime.datetime.now() + datetime.timedelta(
                        seconds=expire_seconds
                    )
                    lock_acquired = True
            if not lock_acquired:
                time.sleep(0.1)
        if not lock_acquired:
            raise AcquireLockException(f"Failed to acquire lock for key: {key}")
        db.session.flush()
        yield
    except sqlalchemy.exc.IntegrityError:
        lock_acquired = False
        raise AcquireLockException(
            f"Failed to acquire lock for key: {key} due to a race condition."
        )
    finally:
        if lock_acquired:
            db.session.query(Lock).filter(Lock.key == key).delete()
            db.session.flush()


class AcquireLockException(Exception):
    """Exception raised when attempting to acquire a held lock."""
