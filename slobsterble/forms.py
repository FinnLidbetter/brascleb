from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    PasswordField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired
from wtforms.widgets import TextArea

from slobsterble.app import db
from slobsterble.models import Player, Dictionary


class LoginForm(FlaskForm):
    """Basic form for logging in a user."""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegisterForm(FlaskForm):
    """Basic form for registering a user."""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired()])
    submit = SubmitField('Register')


class TemporaryPlayForm(FlaskForm):
    """Form for temporary use to test game play."""
    played_tiles_json = StringField('Played tiles json',
                                    widget=TextArea(),
                                    validators=[DataRequired()])
    submit = SubmitField('Play')


class NewGameForm(FlaskForm):
    """Form for starting a new game."""
    opponents = SelectMultipleField('Opponents', coerce=int,
                                    validators=[DataRequired()])
    dictionary = SelectField('Dictionary', coerce=int,
                             validators=[DataRequired()])
    submit = SubmitField('Start Game')


class AddWordForm(FlaskForm):
    """Form for adding a word to a dictionary."""
    dictionary = SelectField('Dictionary', coerce=int,
                             validators=[DataRequired()])
    word = StringField('New Word', validators=[DataRequired()])
    definition = StringField('Definition', widget=TextArea())
    submit = SubmitField('Add Word')


def set_opponent_choices(user_id, new_game_form):
    """Set the possible opponents for a New Game Form."""
    possible_opponents = db.session.query(Player).filter(
        Player.user_id != user_id).all()
    new_game_form.opponents.choices = [
        (player.id, player.display_name) for player in possible_opponents]


def set_dictionary_choices(form):
    """Set the possible dictionaries for a New Game Form."""
    possible_dictionaries = db.session.query(Dictionary).all()
    form.dictionary.choices = [(dictionary.id, dictionary.name)
                               for dictionary in possible_dictionaries]
