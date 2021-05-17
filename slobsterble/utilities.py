from flask import (
    redirect,
    request,
    url_for
)
from flask_admin.contrib.sqla import ModelView
from flask_jwt_extended import verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError


class SlobsterbleModelView(ModelView):
    """Model view class with authentication."""
    form_excluded_columns = ['created', 'modified']

    def is_accessible(self):
        try:
            verify_jwt_in_request()
        except NoAuthorizationError:
            return False
        return True

    def inaccessible_callback(self, name, **kwargs):
        # Redirect to login page if user doesn't have access.
        return redirect(url_for('adminloginview', next=request.url))
