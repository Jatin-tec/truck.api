"""
Centralized permission classes for the truck rental platform.
Use these instead of creating duplicate permission classes in individual apps.
"""
from rest_framework import permissions


class IsCustomer(permissions.BasePermission):
    """Permission for customer-only endpoints"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'customer'


class IsVendor(permissions.BasePermission):
    """Permission for vendor-only endpoints"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'vendor'


class IsManager(permissions.BasePermission):
    """Permission for manager-only endpoints"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'manager'


class IsAdmin(permissions.BasePermission):
    """Permission for admin-only endpoints"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsCustomerOrVendor(permissions.BasePermission):
    """Permission for customer or vendor endpoints"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['customer', 'vendor']


class IsVendorOrManager(permissions.BasePermission):
    """Permission for vendor or manager endpoints"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['vendor', 'manager']


class IsCustomerOrManager(permissions.BasePermission):
    """Permission for customer or manager endpoints"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['customer', 'manager']


class IsVendorOrReadOnly(permissions.BasePermission):
    """Permission for vendor write access or read-only for others"""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == 'vendor'

    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only to vendor owners
        if request.user.role != 'vendor':
            return False
            
        # Check if the object belongs to the vendor
        if hasattr(obj, 'vendor'):
            return obj.vendor == request.user
        
        return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission to only allow owners of an object to edit it.
    Assumes the model has a 'user' or 'owner' field.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only to the owner
        # Handles both 'user' and 'owner' field names
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'owner'):
            return obj.owner == request.user
        elif hasattr(obj, 'vendor'):
            return obj.vendor == request.user
        elif hasattr(obj, 'customer'):
            return obj.customer == request.user
        
        return False


class IsVendorOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission for vendor to edit their own resources or read-only for others.
    Combines vendor role check with ownership check.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == 'vendor'

    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only to vendor owners
        if request.user.role != 'vendor':
            return False

        if hasattr(obj, 'vendor'):
            return obj.vendor == request.user
        
        return False


class IsCustomerOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission for customer to edit their own resources or read-only for others.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == 'customer'

    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only to customer owners
        if request.user.role != 'customer':
            return False

        if hasattr(obj, 'customer'):
            return obj.customer == request.user
        
        return False
