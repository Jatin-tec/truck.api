from django.contrib import admin
from quotations.models import (
    QuotationRequest, Quotation, QuotationNegotiation, 
    QuotationRequestItem, Cart, CartItem, QuotationItem,
    # New route-based models
    Route, RouteStop, RoutePricing, CustomerEnquiry, 
    PriceRange, VendorEnquiryRequest
)

class QuotationRequestItemInline(admin.TabularInline):
    model = QuotationRequestItem
    extra = 0
    readonly_fields = ['created_at']

@admin.register(QuotationRequest)
class QuotationRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'vendor', 'pickup_address', 'delivery_address', 'pickup_date', 'created_at']
    list_filter = ['pickup_date', 'is_active', 'vendor']
    search_fields = ['customer__name', 'vendor__name']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [QuotationRequestItemInline]

class QuotationItemInline(admin.TabularInline):
    model = QuotationItem
    extra = 0
    readonly_fields = ['total_price', 'created_at']

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ['id', 'vendor', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['vendor__name', 'quotation_request__customer__name']
    readonly_fields = ['total_amount', 'created_at', 'updated_at']
    inlines = [QuotationItemInline]

@admin.register(QuotationNegotiation)
class QuotationNegotiationAdmin(admin.ModelAdmin):
    list_display = ['id', 'quotation', 'initiated_by', 'proposed_amount', 'created_at']
    list_filter = ['initiated_by', 'created_at']
    readonly_fields = ['created_at']

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'vendor', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['customer__name', 'vendor__name']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [CartItemInline]

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'cart', 'truck', 'quantity', 'item_weight', 'created_at']
    list_filter = ['created_at']
    search_fields = ['cart__customer__name', 'truck__registration_number']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(QuotationRequestItem)
class QuotationRequestItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'quotation_request', 'truck', 'quantity', 'item_weight', 'created_at']
    list_filter = ['created_at']
    search_fields = ['quotation_request__customer__name', 'truck__registration_number']
    readonly_fields = ['created_at']

@admin.register(QuotationItem)
class QuotationItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'quotation', 'truck', 'quantity', 'total_price', 'created_at']
    list_filter = ['created_at']
    search_fields = ['quotation__vendor__name', 'truck__registration_number']
    readonly_fields = ['total_price', 'created_at']

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
