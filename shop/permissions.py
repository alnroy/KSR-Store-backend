# shop/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminUserOrReadOnly(BasePermission):
    """
    Allows anyone to view (GET), but only Admin users (is_staff) 
    can add, edit, or delete (POST, PUT, DELETE).
    """
    def has_permission(self, request, view):
        # SAFE_METHODS are GET, HEAD, OPTIONS (Reading data)
        if request.method in SAFE_METHODS:
            return True
        # Otherwise, user must be logged in AND be an admin (is_staff)
        return bool(request.user and request.user.is_staff)