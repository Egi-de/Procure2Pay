from django.contrib.auth import get_user_model
from rest_framework import permissions

User = get_user_model()


class RolePermission(permissions.BasePermission):
    allowed_roles: list[str] = []

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if not self.allowed_roles:
            return True
        return request.user.role in self.allowed_roles


class IsStaff(RolePermission):
    allowed_roles = [User.Roles.STAFF]


class IsApprover(RolePermission):
    allowed_roles = [User.Roles.APPROVER_L1, User.Roles.APPROVER_L2]


class IsFinance(RolePermission):
    allowed_roles = [User.Roles.FINANCE]

