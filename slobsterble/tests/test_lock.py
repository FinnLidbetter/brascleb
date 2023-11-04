"""Test the locking mechanism."""

import datetime

import pytest
import sqlalchemy.exc

from slobsterble.models import Lock
from slobsterble.models.lock import acquire_lock, AcquireLockException


def test_lock_unique(db):
    """Two locks cannot be created with the same key."""
    now = datetime.datetime.now()
    expiry_1 = now + datetime.timedelta(seconds=10)
    lock_1 = Lock(key="key1", expiry=expiry_1)
    db.session.add(lock_1)
    db.session.commit()
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        expiry_2 = now + datetime.timedelta(seconds=20)
        lock_2 = Lock(key="key1", expiry=expiry_2)
        db.session.add(lock_2)
        db.session.commit()
    db.session.rollback()
    db.session.query(Lock).filter(Lock.key == "key1").delete()
    db.session.commit()


def test_lock_different_keys(db):
    """Two locks with different keys can co-exist."""
    expiry = datetime.datetime.now() + datetime.timedelta(seconds=10)
    lock_1 = Lock(key="key_something_1", expiry=expiry)
    lock_2 = Lock(key="key_something_2", expiry=expiry)
    db.session.add(lock_1)
    db.session.add(lock_2)
    db.session.commit()
    locks = db.session.query(Lock).all()
    assert any(lock.key == "key_something_1" for lock in locks)
    assert any(lock.key == "key_something_2" for lock in locks)
    db.session.query(Lock).filter(Lock.key == "key_something_1").delete()
    db.session.query(Lock).filter(Lock.key == "key_something_2").delete()
    db.session.commit()


def test_acquire_lock(db):
    """Test trying to acquire an already held lock raises exception."""
    with acquire_lock("test_key"):
        with pytest.raises(
            AcquireLockException, match="Failed to acquire lock for key: test_key"
        ):
            with acquire_lock("test_key"):
                pass
    assert db.session.query(Lock).filter_by(key="test_key").one_or_none() is None


def test_acquire_lock_blocking(db):
    """Blocking allows waiting for a lock to expire."""
    with acquire_lock("blocking_key", expire_seconds=1):
        initial_expiry = (
            db.session.query(Lock).filter_by(key="blocking_key").one().expiry
        )
        with acquire_lock("blocking_key", block_seconds=3):
            new_expiry = (
                db.session.query(Lock).filter_by(key="blocking_key").one().expiry
            )
            assert new_expiry != initial_expiry
    assert db.session.query(Lock).filter_by(key="blocking_key").one_or_none() is None


def test_block_too_short(db):
    """Blocking for not enough time raises an exception."""
    with acquire_lock("blocking_key_2", expire_seconds=60):
        with pytest.raises(
            AcquireLockException, match="Failed to acquire lock for key: blocking_key_2"
        ):
            with acquire_lock("blocking_key_2", block_seconds=1):
                pass
        # The lock is still in place.
        assert (
            db.session.query(Lock).filter_by(key="blocking_key_2").one_or_none()
            is not None
        )
    # The lock is released.
    assert db.session.query(Lock).filter_by(key="blocking_key_2").one_or_none() is None
