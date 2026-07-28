from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOwnReports(BasePermission):
    """
    Custom permission:
    - Superusers/staff can view and update all reports.
    - Regular users can only view their own submitted reports.
    - No one can edit/delete reports they submit.

    Note: This is kept for reference but the views now use method-based
    permissions directly (IsAuthenticated for POST, IsAdminUser for GET/PATCH).
    """

    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return True
        return False

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser:
            return True
        if request.method in SAFE_METHODS:
            return obj.reporter == request.user
        return False

