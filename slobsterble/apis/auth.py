"""Handler for user authentication."""

from flask import (
    Blueprint,
    Response,
    flash,
    redirect,
    render_template,
    request,
    url_for,
    jsonify,
)
from flask_jwt_extended import (
    current_user,
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    unset_jwt_cookies,
)
from flask_restful import Resource
from werkzeug.security import generate_password_hash

from slobsterble.models import (
    BoardLayout,
    Dictionary,
    Distribution,
    Player,
    User,
)
from slobsterble.forms import LoginForm


class TokenRefreshView(Resource):

    @staticmethod
    @jwt_required(refresh=True)
    def post():
        identity = get_jwt_identity()
        access_token = create_access_token(identity=identity, fresh=False)
        return jsonify(access_token=access_token)


class LoginView(Resource):

    @staticmethod
    def post():
        username = request.json.get("username", None)
        password = request.json.get("password", None)

        user = User.query.filter_by(username=username).one_or_none()
        if not user or not user.check_password(password):
            return Response('Incorrect username or password', status=401)

        access_token = create_access_token(identity=user, fresh=True)
        refresh_token = create_refresh_token(identity=user)
        return jsonify(access_token=access_token, refresh_token=refresh_token)


class AdminLoginView(Resource):

    @staticmethod
    def get():
        form = LoginForm()
        return render_template(
            'auth/admin-login.html', title='Sign In', form=form)

    @staticmethod
    def post():
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user is None or not user.check_password(form.password.data):
                flash('Invalid username or password')
                return redirect(url_for('auth.admin_login'))
            response = jsonify({"msg": "login successful"})
            access_token = create_access_token(identity="example_user")
            set_access_cookies(response, access_token)
            return redirect(url_for('index'))
        return render_template('auth/admin-login.html', title='Sign In',
                               form=form)


class AdminLogoutView(Resource):

    @staticmethod
    def get():
        response = jsonify({'msg': 'logout successful'})
        unset_jwt_cookies(response)
        return response


class RegisterView(Resource):

    def post():
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

# @bp.route('/login', methods=('GET', 'POST'))
# def login():
#     if current_user.is_authenticated:
#         return Response(status=200)
#     data = request.get_json()
#     if 'username' not in data or 'password' not in data:
#         return Response('Bad request.', status=401)
#     user = User.query.filter_by(username=data['username']).first()
#     if user is None or not user.check_password(data['password']):
#         return Response("Invalid username or password.", status=400)
#     if login_user(user, remember=data.get('remember', False)):
#         return Response(status=200)
#     return Response("Login failed.", status=400)
#
#
# @bp.route('/admin-login', methods=('GET', 'POST'))
# def admin_login():
#     if current_user.is_authenticated:
#         return redirect(url_for('index'))
#     form = LoginForm()
#     if form.validate_on_submit():
#         user = User.query.filter_by(username=form.username.data).first()
#         if user is None or not user.check_password(form.password.data):
#             flash('Invalid username or password')
#             return redirect(url_for('auth.admin_login'))
#         login_user(user, remember=form.remember_me.data)
#         return redirect(url_for('index'))
#     return render_template('auth/admin-login.html', title='Sign In', form=form)
#
#
# @bp.route('/register', methods=('GET', 'POST'))
# def register():
#     data = request.get_json()
#     expected_fields = ['username', 'password',
#                        'confirmed_password', 'display_name']
#     if not all([field in data for field in expected_fields]):
#         return Response('Bad request', status=401,
#                         mimetype='application/json')
#     existing_user = User.query.filter_by(username=data['username']).first()
#     if existing_user:
#         return Response('User with this username already exists.', status=400)
#     if data['password'] != data['confirmed_password']:
#         return Response('Passwords do not match.', status=400)
#     new_user = User(username=data['username'],
#                     password_hash=generate_password_hash(data['password']))
#     db.session.add(new_user)
#     default_dictionary = db.session.query(Dictionary).filter_by(id=2).first()
#     default_board_layout = db.session.query(BoardLayout).filter_by(
#         name='Classic').first()
#     default_distribution = db.session.query(Distribution).filter_by(
#         name='Classic').first()
#     if default_dictionary is None:
#         return Response('Internal server error.', status=400)
#     new_player = Player(user=new_user, display_name=data['display_name'],
#                         dictionary=default_dictionary,
#                         board_layout=default_board_layout,
#                         distribution=default_distribution)
#     db.session.add(new_player)
#     db.session.commit()
#     return Response('Success!', status=200)
#
#
# @bp.route('/logout')
# def logout():
#     logout_user()
#     return Response(status=200)
#