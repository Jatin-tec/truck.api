from rest_framework import generics, status, permissions
from project.permissions import IsCustomer, IsVendor, IsCustomerOrVendor
