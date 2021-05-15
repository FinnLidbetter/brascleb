"""Handler for user authentication."""

from flask import (
    Blueprint,
    Response,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for)
from flask_restful import Resource
from werkzeug.security import generate_password_hash

from slobsterble.app import auth, db
from slobsterble.models import (
    BoardLayout,
    Dictionary,
    Distribution,
    Player,
    User,
)
from slobsterble.forms import LoginForm

bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth.verify_password
def verify_password(username_or_token, password):
    """Authenticate a user."""
    # First try to authenticate by token
    user = User.verify_auth_token(username_or_token)
    if not user:
        # Try to authenticate with username/password
        user = User.query.filter_by(username=username_or_token).first()
        if not user or not user.verify_password(password):
            return False
    g.user = user
    return True

class TokenView(Resource):

    @staticmethod
    @auth.login_required
    def post():


@bp.route('/login', methods=('GET', 'POST'))
def login():
    if current_user.is_authenticated:
        return Response(status=200)
    data = request.get_json()
    if 'username' not in data or 'password' not in data:
        return Response('Bad request.', status=401)
    user = User.query.filter_by(username=data['username']).first()
    if user is None or not user.check_password(data['password']):
        return Response("Invalid username or password.", status=400)
    if login_user(user, remember=data.get('remember', False)):
        return Response(status=200)
    return Response("Login failed.", status=400)


@bp.route('/admin-login', methods=('GET', 'POST'))
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('auth.admin_login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('index'))
    return render_template('auth/admin-login.html', title='Sign In', form=form)


@bp.route('/register', methods=('GET', 'POST'))
def register():
    data = request.get_json()
    expected_fields = ['username', 'password',
                       'confirmed_password', 'display_name']
    if not all([field in data for field in expected_fields]):
        return Response('Bad request', status=401,
                        mimetype='application/json')
    existing_user = User.query.filter_by(username=data['username']).first()
    if existing_user:
        return Response('User with this username already exists.', status=400)
    if data['password'] != data['confirmed_password']:
        return Response('Passwords do not match.', status=400)
    new_user = User(username=data['username'],
                    password_hash=generate_password_hash(data['password']))
    db.session.add(new_user)
    default_dictionary = db.session.query(Dictionary).filter_by(id=2).first()
    default_board_layout = db.session.query(BoardLayout).filter_by(
        name='Classic').first()
    default_distribution = db.session.query(Distribution).filter_by(
        name='Classic').first()
    if default_dictionary is None:
        return Response('Internal server error.', status=400)
    new_player = Player(user=new_user, display_name=data['display_name'],
                        dictionary=default_dictionary,
                        board_layout=default_board_layout,
                        distribution=default_distribution)
    db.session.add(new_player)
    db.session.commit()
    return Response('Success!', status=200)


@bp.route('/logout')
def logout():
    logout_user()
    return Response(status=200)
