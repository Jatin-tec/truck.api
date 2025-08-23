from django.db import models
from django.conf import settings
from trucks.models import Truck, TruckType
from .enums import QuotationStatus, NegotiationInitiator, UrgencyLevel, WeightUnit

class QuotationRequest(models.Model):
    """Customer's order request - unique for origin-destination and pickup-drop date"""
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quotation_requests',
        limit_choices_to={'role': 'customer'},
        null=True, blank=True,
    )
    
    # Search parameters that make this request unique
    origin_pincode = models.CharField(max_length=10, default='000000')
    destination_pincode = models.CharField(max_length=10, default='000000') 
    pickup_date = models.DateField(default='2024-01-01')
    drop_date = models.DateField(default='2024-01-01')
    weight = models.DecimalField(max_digits=8, decimal_places=2, help_text="Weight", default=0)
    weight_unit = models.CharField(max_length=10, choices=WeightUnit.choices, default=WeightUnit.KG)
    vehicle_type = models.CharField(max_length=50, help_text="Type of vehicle needed", default='Truck')

    # Pickup details
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_address = models.TextField(blank=True)
    
    # Delivery details
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_address = models.TextField(blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['customer', 'origin_pincode', 'destination_pincode', 'pickup_date', 'drop_date']

    def __str__(self):
        return f"Quote Request {self.id} - {self.origin_pincode} to {self.destination_pincode} on {self.pickup_date}"

    def get_total_quotations(self):
        """Get total number of quotations for this request"""
        return self.quotations.count()

class Quotation(models.Model):
    """Vendor's quotation for a quotation request"""

    quotation_request = models.ForeignKey(
        QuotationRequest, 
        on_delete=models.CASCADE, 
        related_name='quotations',
        null=True,
        blank=True,
    )
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quotations',
        limit_choices_to={'role': 'vendor'}
    )
    
    # Store vendor name for performance (avoid joins)
    vendor_name = models.CharField(max_length=100, help_text="Cached vendor name")
    
    # Overall pricing details
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    # Terms
    terms_and_conditions = models.TextField(blank=True)
    validity_hours = models.PositiveIntegerField(default=24, help_text="Quote validity in hours")
    
    # Urgency and Status
    urgency_level = models.CharField(max_length=20, choices=UrgencyLevel.choices, default=UrgencyLevel.MEDIUM)
    status = models.CharField(max_length=20, choices=QuotationStatus.choices, default=QuotationStatus.PENDING)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Additional details
    cargo_description = models.TextField(blank=True)
    special_instructions = models.TextField(blank=True)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['quotation_request', 'vendor']

    def __str__(self):
        return f"Quotation {self.id} - ₹{self.total_amount}"

class QuotationItem(models.Model):
    """Vehicle item included in a quotation - stores only quote-specific data"""
    quotation = models.ForeignKey(
        Quotation,
        on_delete=models.CASCADE,
        related_name='items'
    )
    
    # Vehicle reference - either specific truck OR truck type for flexible quotes
    truck = models.ForeignKey(
        'trucks.Truck',
        on_delete=models.SET_NULL,
        related_name='quotation_items',
        null=True, blank=True,
        help_text="Specific truck if assigned"
    )
    truck_type = models.ForeignKey(
        'trucks.TruckType',
        on_delete=models.CASCADE,
        related_name='quotation_items',
        null=True, blank=True,
        help_text="Truck type for flexible quotes"
    )
    
    # Quote-specific operational details
    quantity = models.PositiveIntegerField(default=1, help_text="Number of vehicles of this type")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Quoted price per vehicle")
    
    # Quote-specific delivery details
    estimated_delivery = models.DateField(null=True, blank=True, help_text="Estimated delivery date for this item")
    pickup_locations = models.JSONField(default=list, blank=True, help_text="Specific pickup locations for this item")
    drop_locations = models.JSONField(default=list, blank=True, help_text="Specific drop locations for this item")
    
    # Optional quote-specific notes
    special_instructions = models.TextField(blank=True, help_text="Special instructions for this vehicle item")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']
        constraints = [
            models.CheckConstraint(
                check=models.Q(truck__isnull=False) | models.Q(truck_type__isnull=False),
                name='quotation_item_must_have_truck_or_type'
            )
        ]

    def __str__(self):
        if self.truck:
            vehicle_info = f"{self.truck.make} {self.truck.model} ({self.truck.registration_number})"
        else:
            vehicle_info = f"{self.truck_type.name}"
        return f"{self.quantity}x {vehicle_info} - ₹{self.unit_price} (Quotation {self.quotation.id})"
    
    def get_total_price(self):
        """Calculate total price for this item"""
        return self.quantity * self.unit_price
    
    def get_vehicle_details(self):
        """Get vehicle specifications from the related truck or truck type"""
        if self.truck:
            return {
                'type': self.truck.truck_type.name,
                'make': self.truck.make,
                'model': self.truck.model,
                'capacity': self.truck.capacity,
                'registration_number': self.truck.registration_number,
                'year': self.truck.year,
                'availability_status': self.truck.availability_status
            }
        elif self.truck_type:
            return {
                'type': self.truck_type.name,
                'description': self.truck_type.description,
                'make': None,
                'model': None,
                'capacity': None,
                'registration_number': None,
                'year': None,
                'availability_status': 'available'  # Generic truck type is assumed available
            }
        return {}

    def __str__(self):
        vehicle_info = self.vehicle_model or self.vehicle_type or f"Vehicle {self.vehicle_id}"
        return f"{self.quantity}x {vehicle_info} - ₹{self.unit_price} (Quotation {self.quotation.id})"
    
    def get_total_price(self):
        """Calculate total price for this item"""
        return self.quantity * self.unit_price

class QuotationNegotiation(models.Model):
    """Track negotiation history between customer and vendor"""

    quotation = models.ForeignKey(
        Quotation, 
        on_delete=models.CASCADE, 
        related_name='negotiations'
    )
    initiated_by = models.CharField(max_length=10, choices=NegotiationInitiator.choices)
    proposed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    message = models.TextField(blank=True)
    
    # Breakdown of proposed changes (optional)
    proposed_base_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    proposed_fuel_charges = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    proposed_toll_charges = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    proposed_loading_charges = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    proposed_unloading_charges = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    proposed_additional_charges = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Negotiation for Quotation {self.quotation.id} by {self.initiated_by}"


class Route(models.Model):
    """Vendor's predefined routes with stops"""
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='routes',
        limit_choices_to={'role': 'vendor'}
    )
    
    # Route details
    route_name = models.CharField(max_length=200, help_text="e.g., Mumbai to Delhi via Pune")
    origin_city = models.CharField(max_length=100)
    origin_state = models.CharField(max_length=100)
    origin_pincode = models.CharField(max_length=10, null=True, blank=True, help_text="Primary pincode for origin city")
    origin_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    origin_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    
    destination_city = models.CharField(max_length=100)
    destination_state = models.CharField(max_length=100)
    destination_pincode = models.CharField(max_length=10, null=True, blank=True, help_text="Primary pincode for destination city")
    destination_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    destination_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    
    # Route characteristics
    total_distance_km = models.DecimalField(max_digits=8, decimal_places=2)
    estimated_duration_hours = models.DecimalField(max_digits=5, decimal_places=1)
    route_frequency = models.CharField(max_length=20, choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
        ('on_demand', 'On Demand')
    ], default='weekly')
    
    # Operational details
    is_active = models.BooleanField(default=True)
    max_vehicles_per_trip = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['vendor', 'origin_city', 'destination_city']
        ordering = ['vendor', 'route_name']

    def __str__(self):
        return f"{self.vendor.name}: {self.route_name}"

class RouteStop(models.Model):
    """Intermediate stops in a route"""
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stops')

    stop_city = models.CharField(max_length=100)
    stop_state = models.CharField(max_length=100)
    stop_pincode = models.CharField(max_length=10, null=True, blank=True, help_text="Primary pincode for stop city")
    stop_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    stop_longitude = models.DecimalField(max_digits=9, decimal_places=6)

    # Position in route (1, 2, 3, etc.)
    stop_order = models.PositiveIntegerField()
    distance_from_origin = models.DecimalField(max_digits=8, decimal_places=2)
    distance_to_destination = models.DecimalField(max_digits=8, decimal_places=2)

    # Operational details
    estimated_arrival_time = models.DecimalField(max_digits=4, decimal_places=1, help_text="Hours from origin")
    can_pickup = models.BooleanField(default=True)
    can_drop = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['route', 'stop_order']
        ordering = ['route', 'stop_order']

    def __str__(self):
        return f"{self.route.route_name} - Stop {self.stop_order}: {self.stop_city}"

class RoutePricing(models.Model):
    """Pricing for different segments of a route"""
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='pricing')
    truck_type = models.ForeignKey(TruckType, on_delete=models.CASCADE)
    
    # Route segment (can be origin to destination or origin to any stop)
    from_city = models.CharField(max_length=100)
    to_city = models.CharField(max_length=100)
    segment_distance_km = models.DecimalField(max_digits=8, decimal_places=2)
    
    # Pricing details
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_km = models.DecimalField(max_digits=8, decimal_places=2)
    fuel_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    toll_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    loading_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unloading_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Price ranges for different scenarios
    min_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Minimum price for this segment")
    max_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Maximum price for this segment")
    
    # Availability and capacity
    max_weight_capacity = models.DecimalField(max_digits=8, decimal_places=2)
    available_vehicles = models.PositiveIntegerField(default=1)
    
    # Operational details
    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['route', 'truck_type', 'from_city', 'to_city']
        ordering = ['route', 'from_city', 'to_city']

    def __str__(self):
        return f"{self.route.route_name} - {self.truck_type.name}: {self.from_city} to {self.to_city}"

    def get_total_price(self):
        """Calculate total price for this segment"""
        return (self.base_price + self.fuel_charges + self.toll_charges + 
                self.loading_charges + self.unloading_charges)

class CustomerEnquiry(models.Model):
    """Customer enquiry without vendor visibility"""
    ENQUIRY_STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('quotes_generated', 'Quotes Generated'),
        ('quote_selected', 'Quote Selected'),
        ('sent_to_vendors', 'Sent to Vendors'),
        ('vendor_responses', 'Vendor Responses Received'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]
    
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enquiries',
        limit_choices_to={'role': 'customer'}
    )
    
    # Trip details
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6, default=0.0)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6, default=0.0)
    pickup_address = models.TextField()
    pickup_city = models.CharField(max_length=100)
    pickup_state = models.CharField(max_length=100)
    pickup_pincode = models.CharField(max_length=10, null=True, blank=True, help_text="Pickup pincode")
    pickup_date = models.DateTimeField()
    
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6, default=0.0)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6, default=0.0)
    delivery_address = models.TextField()
    delivery_city = models.CharField(max_length=100)
    delivery_state = models.CharField(max_length=100)
    delivery_pincode = models.CharField(max_length=10, null=True, blank=True, help_text="Delivery pincode")
    expected_delivery_date = models.DateTimeField()
    
    # Vehicle requirements
    truck_type = models.ForeignKey(TruckType, on_delete=models.CASCADE)
    number_of_vehicles = models.PositiveIntegerField(default=1)
    total_weight = models.DecimalField(max_digits=8, decimal_places=2)
    cargo_description = models.TextField()
    special_instructions = models.TextField(blank=True)
    
    # Route matching
    estimated_distance_km = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    matched_routes = models.ManyToManyField(Route, blank=True, related_name='enquiries')
    is_miscellaneous_route = models.BooleanField(default=False, help_text="Route not covered by regular vendors")
    
    # Status and management
    status = models.CharField(max_length=20, choices=ENQUIRY_STATUS_CHOICES, default='submitted')
    assigned_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_enquiries',
        limit_choices_to={'role': 'manager'}
    )
    
    # Customer preferences
    budget_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    budget_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    preferred_vendor_size = models.CharField(max_length=20, choices=[
        ('small', 'Small Vendor'),
        ('medium', 'Medium Vendor'),
        ('large', 'Large Vendor'),
        ('any', 'Any Size')
    ], default='any')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Enquiry {self.id}: {self.pickup_city} to {self.delivery_city} ({self.customer.name})"


class PriceRange(models.Model):
    """System-generated price ranges for customer enquiries"""
    CHANCE_LEVELS = [
        ('low', 'Low (10-30%)'),
        ('medium', 'Medium (40-70%)'),
        ('high', 'High (80-95%)'),
    ]
    
    enquiry = models.ForeignKey(CustomerEnquiry, on_delete=models.CASCADE, related_name='price_ranges')
    
    # Price range details
    min_price = models.DecimalField(max_digits=10, decimal_places=2)
    max_price = models.DecimalField(max_digits=10, decimal_places=2)
    recommended_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Availability information
    vehicles_available = models.PositiveIntegerField()
    vendors_count = models.PositiveIntegerField()
    chance_of_getting_deal = models.CharField(max_length=10, choices=CHANCE_LEVELS)
    
    # Route information (without vendor details)
    route_type = models.CharField(max_length=20, choices=[
        ('direct', 'Direct Route'),
        ('via_stops', 'Via Multiple Stops'),
        ('miscellaneous', 'Non-standard Route')
    ])
    estimated_duration_hours = models.DecimalField(max_digits=5, decimal_places=1)
    
    # Supporting vendors (hidden from customer)
    supporting_routes = models.ManyToManyField(Route, blank=True)
    
    # Additional details
    includes_fuel = models.BooleanField(default=True)
    includes_tolls = models.BooleanField(default=True)
    includes_loading = models.BooleanField(default=True)
    additional_charges_note = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['min_price']

    def __str__(self):
        return f"₹{self.min_price}-₹{self.max_price} ({self.chance_of_getting_deal} chance)"
