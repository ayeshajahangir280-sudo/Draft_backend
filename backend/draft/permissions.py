from rest_framework.permissions import BasePermission

from .models import UserRole


def user_role(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_staff or user.is_superuser:
        return UserRole.ADMIN
    return getattr(getattr(user, "profile", None), "role", None)


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return user_role(request.user) == UserRole.ADMIN


class IsManagerRole(BasePermission):
    def has_permission(self, request, view):
        return user_role(request.user) == UserRole.MANAGER
