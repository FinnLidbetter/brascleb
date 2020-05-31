"""
Data migration to create an extendable unix dictionary.

Revision ID: 3ea1bfba1ae7
Revises: ab048cb85789
Create Date: 2020-06-11 21:16:27.361069

"""
import os
import sys

from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm

from slobsterble.models import Dictionary, Entry


# revision identifiers, used by Alembic.
revision = '3ea1bfba1ae7'
down_revision = 'c2a7026b0899'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    base_dictionary = Dictionary(name='Unix Dictionary')
    with open(os.path.abspath('dictionaries/unix_dictionary.txt')) as unix_dictionary_file:
        words = unix_dictionary_file.readlines()
        words = [word.rstrip() for word in words]
        for word in words:
            entry = Entry(word=word)
            base_dictionary.entries.append(entry)
            session.add(entry)
    session.add(base_dictionary)
    session.commit()
    # ### end Alembic commands ###


def downgrade():
    pass
    # ### end Alembic commands ###
