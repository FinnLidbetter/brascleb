from flask import (
    redirect,
    request,
    url_for
)
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user


class SlobsterbleModelView(ModelView):
    """Model view class with authentication."""
    form_excluded_columns = ['created', 'modified']

    def is_accessible(self):
        return current_user.is_authenticated and current_user.activated

    def inaccessible_callback(self, name, **kwargs):
        # Redirect to login page if user doesn't have access.
        return redirect(url_for('login', next=request.url))
