from django.contrib import admin
from trucks.models import TruckType, Truck, TruckImage, Driver, TruckLocation

@admin.register(TruckType)
class TruckTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name']

@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    list_display = ['registration_number', 'truck_type', 'vendor', 'capacity', 'availability_status', 'created_at']
    list_filter = ['truck_type', 'availability_status', 'is_active']
    search_fields = ['registration_number', 'vendor__name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(TruckImage)
class TruckImageAdmin(admin.ModelAdmin):
    list_display = ['truck', 'caption', 'is_primary', 'created_at']
    list_filter = ['is_primary']

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ['name', 'license_number', 'vendor', 'assigned_truck', 'is_available', 'created_at']
    list_filter = ['is_available', 'is_active']
    search_fields = ['name', 'license_number', 'vendor__name']

@admin.register(TruckLocation)
class TruckLocationAdmin(admin.ModelAdmin):
    list_display = ['truck', 'latitude', 'longitude', 'timestamp']
    list_filter = ['timestamp']
    readonly_fields = ['timestamp']
