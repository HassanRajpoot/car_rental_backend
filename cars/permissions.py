from rest_framework import permissions

class IsFleetManagerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow fleet managers to edit cars.
    """
    
    def has_permission(self, request, view):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for fleet managers
        return (request.user.is_authenticated and 
                hasattr(request.user, 'is_fleet') and 
                request.user.is_fleet())
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for the owner
        return obj.owner == request.user