from django.contrib import admin
from quotations.models import (
    QuotationRequest, Quotation, QuotationNegotiation, 
    # New route-based models
    Route, RouteStop, RoutePricing, CustomerEnquiry, 
    PriceRange, VendorEnquiryRequest
)

@admin.register(QuotationRequest)
class QuotationRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'origin_pincode', 'destination_pincode', 'pickup_date', 'drop_date', 'created_at']
    list_filter = ['pickup_date', 'drop_date', 'is_active', 'urgency_level', 'vehicle_type']
    search_fields = ['customer__name', 'origin_pincode', 'destination_pincode']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ['id', 'vendor_name', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['vendor_name', 'quotation_request__customer__name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(QuotationNegotiation)
class QuotationNegotiationAdmin(admin.ModelAdmin):
    list_display = ['id', 'quotation', 'initiated_by', 'proposed_amount', 'created_at']
    list_filter = ['initiated_by', 'created_at']
    readonly_fields = ['created_at']

# Cart models have been removed from the system


# NEW TRACKING TRUCKS WORKFLOW - Admin Classes

class RouteStopInline(admin.TabularInline):
    model = RouteStop
    extra = 0
    readonly_fields = ['created_at']

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ['id', 'vendor', 'route_name', 'origin_city', 'destination_city', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'vendor']
    search_fields = ['route_name', 'vendor__name', 'origin_city', 'destination_city']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [RouteStopInline]

@admin.register(RouteStop)
class RouteStopAdmin(admin.ModelAdmin):
    list_display = ['id', 'route', 'stop_city', 'stop_order', 'created_at']
    list_filter = ['created_at']
    search_fields = ['route__route_name', 'stop_city']
    readonly_fields = ['created_at']

@admin.register(RoutePricing)
class RoutePricingAdmin(admin.ModelAdmin):
    list_display = ['id', 'route', 'truck_type', 'min_price', 'max_price', 'created_at']
    list_filter = ['truck_type', 'created_at']
    search_fields = ['route__route_name', 'truck_type__name']
    readonly_fields = ['created_at']

@admin.register(CustomerEnquiry)
class CustomerEnquiryAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'pickup_city', 'delivery_city', 'pickup_date', 'status', 'created_at']
    list_filter = ['status', 'pickup_date', 'created_at']
    search_fields = ['customer__name', 'pickup_city', 'delivery_city']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(PriceRange)
class PriceRangeAdmin(admin.ModelAdmin):
    list_display = ['id', 'enquiry', 'min_price', 'max_price', 'chance_of_getting_deal', 'created_at']
    list_filter = ['chance_of_getting_deal', 'created_at']
    search_fields = ['enquiry__customer__name']
    readonly_fields = ['created_at']

@admin.register(VendorEnquiryRequest)
class VendorEnquiryRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'enquiry', 'vendor', 'status', 'vendor_response_price', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['enquiry__customer__name', 'vendor__name']
    readonly_fields = ['created_at', 'updated_at']

# LEGACY MODELS - Marked for deprecation
