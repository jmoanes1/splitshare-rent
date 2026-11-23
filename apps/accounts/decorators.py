"""
Role-based access decorators.

These are enforced on the server in every view. Hiding links in
templates is never treated as a security control.
"""

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.contrib import messages
from django.shortcuts import redirect

from apps.accounts.models import User


def role_required(*roles):
    """Allow only authenticated users whose role is one of ``roles``."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect_to_login(request.path)
            if user.role not in roles:
                messages.error(request, 'You do not have access to that page.')
                return redirect('dashboard')
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def renter_required(view):
    return role_required(User.Role.RENTER)(view)


def owner_required(view):
    return role_required(User.Role.OWNER)(view)


def admin_required(view):
    """Allow only administrators (staff / superuser / ADMIN role)."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect_to_login(request.path)
        if not (user.is_staff or user.is_superuser or user.role == User.Role.ADMIN):
            messages.error(request, 'You do not have access to that page.')
            return redirect('dashboard')
        return view(request, *args, **kwargs)

    return wrapper
