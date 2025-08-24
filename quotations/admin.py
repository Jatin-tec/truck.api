from django.contrib import admin
from quotations.models import (
    QuotationRequest, Quotation, QuotationNegotiation, QuotationItem, 
    # New route-based models
    Route, RouteStop, RoutePricing, CustomerEnquiry, 
    PriceRange
)

@admin.register(QuotationRequest)
class QuotationRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'origin_pincode', 'destination_pincode', 'pickup_date', 'drop_date', 'created_at']
    list_filter = ['pickup_date', 'drop_date', 'is_active', 'vehicle_type']
    search_fields = ['customer__name', 'origin_pincode', 'destination_pincode']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ['id', 'total_amount', 'urgency_level', 'status', 'created_at']
    list_filter = ['status', 'urgency_level', 'created_at']
    search_fields = ['quotation_request__customer__name']
    readonly_fields = ['created_at', 'updated_at']

    

@admin.register(QuotationNegotiation)
class QuotationNegotiationAdmin(admin.ModelAdmin):
    list_display = ['id', 'quotation', 'initiated_by', 'proposed_amount', 'created_at']
    list_filter = ['initiated_by', 'created_at']
    readonly_fields = ['created_at']

@admin.register(QuotationItem)
class QuotationItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'quotation', 'get_vehicle_info', 'quantity', 'unit_price', 'get_total_price', 'created_at']
    list_filter = ['created_at', 'truck_type']
    search_fields = ['quotation__id', 'truck__registration_number', 'truck_type__name']
    readonly_fields = ['created_at', 'updated_at', 'get_total_price']
    
    def get_vehicle_info(self, obj):
        if obj.truck:
            return f"{obj.truck.make} {obj.truck.model} ({obj.truck.registration_number})"
        elif obj.truck_type:
            return f"Type: {obj.truck_type.name}"
        return "No vehicle assigned"
    get_vehicle_info.short_description = 'Vehicle'
    
    def get_total_price(self, obj):
        return f"₹{obj.get_total_price()}"
    get_total_price.short_description = 'Total Price'


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