"""Handler for user authentication."""

from flask import (
  Blueprint,
  flash,
  redirect,
  render_template,
  url_for)
from flask_login import current_user, login_user, logout_user
from werkzeug.security import generate_password_hash

from slobsterble import db
from slobsterble.forms import LoginForm, RegisterForm
from slobsterble.models import User

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=('GET', 'POST'))
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('index'))
    return render_template('auth/login.html', title='Sign In', form=form)


@bp.route('/register', methods=('GET', 'POST'))
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(
            username=form.username.data).first()
        if existing_user:
            flash('User with this username already exists.')
            return redirect(url_for('auth.register'))
        if form.password.data != form.confirm_password.data:
            flash('Passwords do not match.')
            return redirect(url_for('auth.register'))
        new_user = User(
            username=form.username.data,
            password_hash=generate_password_hash(form.password.data))
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('auth/register.html', title='Register', form=form)


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))
