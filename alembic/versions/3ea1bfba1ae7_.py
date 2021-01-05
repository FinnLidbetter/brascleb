"""
Data migration to create YAWL and ENABLE dictionaries.

Revision ID: 3ea1bfba1ae7
Revises: d0b23f92aa9d
Create Date: 2020-06-11 21:16:27.361069

"""
import os
import sys
from collections import defaultdict

from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm

sys.path.append(os.getcwd())
from slobsterble.models import Dictionary, Entry


# revision identifiers, used by Alembic.
revision = '3ea1bfba1ae7'
down_revision = 'd0b23f92aa9d'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    dictionary_names = {'ENABLE (North American)': 'enable.txt',
                        'YAWL (Extended)': 'yawl.txt'}
    dict_words = defaultdict(list)
    entries = {}
    for dictionary_name, path in dictionary_names.items():
        dictionary = Dictionary(name=dictionary_name)
        with open(os.path.abspath('dictionaries/%s' % path)) as dictionary_file:
            file_words = dictionary_file.readlines()
            file_words = [word.rstrip().lower() for word in file_words]
            for word in file_words:
                if word not in entries:
                    entry = Entry(word=word)
                    entries[word] = entry
                    session.add(entry)
                dict_words[dictionary].append(word)
    for dictionary, words in dict_words.items():
        for word in words:
            dictionary.entries.append(entries[word])
        session.add(dictionary)
    session.commit()
    # ### end Alembic commands ###


def downgrade():
    pass
    # ### end Alembic commands ###
