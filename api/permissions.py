from rest_framework import permissions

class IsProjectOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user

class IsProjectManagerOrOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.owner == request.user:
            return True
        return request.user in obj.managers.all()

class IsAssigneeOrProjectManagerOrOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.assignee == request.user:
            return True
        if obj.project.owner == request.user:
            return True
        if request.user in obj.project.managers.all():
            return True
        if request.user.is_staff and request.method in permissions.SAFE_METHODS:
             return True
        return False


class IsAssigneeOrProjectOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return obj.project.owner == request.user or obj.assignee == request.user or request.user.is_staff
        return obj.project.owner == request.user or obj.assignee == request.user


class IsTaskAssignee(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.assignee == request.user


class IsWorkLogOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user

class IsTeamOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if hasattr(obj, 'owner'):
             return obj.owner == request.user
        if hasattr(obj, 'team') and hasattr(obj.team, 'owner'):
            return obj.team.owner == request.user
        return False

class IsTeamMemberUserOrTeamOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if obj.user == request.user:
            return True
        if obj.team.owner == request.user:
            return True
        return False


class IsCommentOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user
