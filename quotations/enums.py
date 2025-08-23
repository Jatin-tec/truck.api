"""
Enums and choices for quotations app.
Centralizes all status choices and business rules.
"""
from django.db import models


class QuotationStatus(models.TextChoices):
    """Status choices for Quotation model"""
    PENDING = 'pending', 'Pending Vendor Response'
    SENT = 'sent', 'Sent to Customer'
    NEGOTIATING = 'negotiating', 'Under Negotiation'
    ACCEPTED = 'accepted', 'Accepted'
    REJECTED = 'rejected', 'Rejected'
    EXPIRED = 'expired', 'Expired'


class NegotiationInitiator(models.TextChoices):
    """Who can initiate negotiations"""
    CUSTOMER = 'customer', 'Customer'
    VENDOR = 'vendor', 'Vendor'


class UrgencyLevel(models.TextChoices):
    """Urgency levels for quotations"""
    LOW = 'low', 'Low Priority'
    MEDIUM = 'medium', 'Medium Priority'
    HIGH = 'high', 'High Priority'
    URGENT = 'urgent', 'Urgent'


class WeightUnit(models.TextChoices):
    """Weight unit choices"""
    KG = 'kg', 'Kilogram'
    TON = 'ton', 'Ton'
    LBS = 'lbs', 'Pounds'


class BusinessRules:
    """Business rules and constants"""
    
    # Negotiation rules
    MAX_NEGOTIATION_VARIANCE_PERCENT = 50
    DEFAULT_QUOTATION_VALIDITY_HOURS = 24
    
    # Status transition rules
    NEGOTIABLE_STATUSES = [QuotationStatus.SENT, QuotationStatus.NEGOTIATING]
    FINAL_STATUSES = [QuotationStatus.ACCEPTED, QuotationStatus.REJECTED, QuotationStatus.EXPIRED]
    
    @staticmethod
    def can_transition_to_negotiating(current_status):
        """Check if quotation can transition to negotiating status"""
        return current_status in BusinessRules.NEGOTIABLE_STATUSES
    
    @staticmethod
    def can_accept_or_reject(current_status):
        """Check if quotation can be accepted or rejected"""
        return current_status in BusinessRules.NEGOTIABLE_STATUSES
    
    @staticmethod
    def is_final_status(status):
        """Check if status is final (no further changes allowed)"""
        return status in BusinessRules.FINAL_STATUSES


class ErrorMessages:
    """Centralized error messages for consistency"""
    
    # Validation errors
    VENDOR_NOT_FOUND = "Vendor not found or invalid role"
    INVALID_DATE_RANGE = "Drop date must be after pickup date"
    NO_ITEMS_PROVIDED = "At least one vehicle item is required"
    NEGATIVE_AMOUNT = "Proposed amount must be positive"
    
    # Business rule errors
    CANNOT_NEGOTIATE_STATUS = "Cannot negotiate quotation with status '{status}'"
    CANNOT_ACCEPT_OWN_NEGOTIATION = "You cannot accept your own negotiation offer"
    CONSECUTIVE_NEGOTIATION = "Cannot negotiate consecutively. Wait for {other_party} response"
    EXCESSIVE_VARIANCE = "Proposed amount varies by {variance:.1f}% from original. Maximum allowed is {max_variance}%"
    
    # Permission errors
    NOT_YOUR_QUOTATION = "You can only negotiate quotations for your own requests"
    NOT_YOUR_VENDOR_QUOTATION = "You can only negotiate your own quotations"
    ROLE_NOT_ALLOWED = "Only customers and vendors can create negotiations"


class ResponseMessages:
    """Centralized success messages for consistency"""
    
    QUOTATION_CREATED = "Quotation request created for vendor {vendor_name} with selected vehicles"
    QUOTATION_UPDATED = "Updated quotation request for vendor {vendor_name}"
    QUOTATION_ACCEPTED = "Quotation accepted successfully. Final amount: ₹{amount}"
    QUOTATION_REJECTED = "Quotation rejected successfully"
    NEGOTIATION_CREATED = "Negotiation offer created successfully by {initiator}"
    NEGOTIATION_ACCEPTED = "Negotiation accepted! Final amount: ₹{amount}"
    NO_NEGOTIATIONS_FOUND = "No negotiations found for this quotation"
    NEGOTIATIONS_FOUND = "Found {count} negotiations for quotation"
