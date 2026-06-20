"""Role-based access control decorators."""
from functools import wraps

from flask import abort
from flask_login import current_user


def role_required(*roles):
    """Allow the view only for the given roles."""
    def wrapper(fn):
        @wraps(fn)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return decorated
    return wrapper


def committee_required(fn):
    """Only Committee members create/edit requests."""
    from . import constants as C

    @wraps(fn)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.role != C.ROLE_COMMITTEE:
            abort(403)
        return fn(*args, **kwargs)
    return decorated
