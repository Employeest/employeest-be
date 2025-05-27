from rest_framework import permissions


class IsProjectOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


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
