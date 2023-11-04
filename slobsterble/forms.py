from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    PasswordField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    """Basic form for logging in a user."""

    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class RegisterForm(FlaskForm):
    """Basic form for registering a user."""

    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired()])
    display_name = StringField("Display name", validators=[DataRequired()])
    submit = SubmitField("Register")


class VerifyEmailForm(FlaskForm):
    """Basic form for verifying the email address for a user."""

    username = StringField("Username", validators=[DataRequired()])
    token = StringField("Token", validators=[DataRequired()])
    submit = SubmitField("Verify Email")


class PasswordResetForm(FlaskForm):
    """Basic form for resetting the password for a user."""

    username = StringField("Username", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[DataRequired()])
    confirm_password = PasswordField(
        "Confirm New Password", validators=[DataRequired()]
    )
    token = StringField("Token", validators=[DataRequired()])
    submit = SubmitField("Reset Password")
