from rest_framework.permissions import BasePermission


class IsBankOperator(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "bank_sampah_id", None) is not None
        )
