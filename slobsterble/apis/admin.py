"""Model view class for the admin view."""

from flask import (
    redirect,
    request,
    url_for
)
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user as session_current_user


class SlobsterbleModelView(ModelView):
    """Model view class with authentication."""
    form_excluded_columns = ['created', 'modified']

    def is_accessible(self):
        """Return true iff the requesting user may access the admin view."""
        return session_current_user.is_authenticated and session_current_user.activated

    def inaccessible_callback(self, name, **kwargs):
        """Redirect to login page if the user is not authorized."""
        return redirect(url_for('adminloginview', next=request.url))
