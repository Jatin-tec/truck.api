from rest_framework import generics, status, permissions

class IsCustomer(permissions.BasePermission):
    """Permission for customer-only endpoints"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'customer'

class IsVendor(permissions.BasePermission):
    """Permission for vendor-only endpoints"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'vendor'


class IsCustomerOrVendor(permissions.BasePermission):
    """Permission for customer or vendor endpoints"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['customer', 'vendor']
