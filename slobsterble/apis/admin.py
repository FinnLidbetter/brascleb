"""Model view class for the admin view."""

from flask import (
    redirect,
    request,
    url_for
)
from flask_admin.contrib.sqla import ModelView
from flask_jwt_extended import verify_jwt_in_request, current_user
from flask_jwt_extended.exceptions import NoAuthorizationError


class SlobsterbleModelView(ModelView):
    """Model view class with authentication."""
    form_excluded_columns = ['created', 'modified']

    def is_accessible(self):
        """Return true iff the requesting user may access the admin view."""
        try:
            verify_jwt_in_request(fresh=True)
            if not current_user.activated:
                return False
        except NoAuthorizationError:
            return False
        return True

    def inaccessible_callback(self, name, **kwargs):
        """Redirect to login page if the user is not authorized."""
        return redirect(url_for('adminloginview', next=request.url))
