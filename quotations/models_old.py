from django.db import models
from django.conf import settings
from trucks.models import Truck, TruckType

class OrderRequest(models.Model):
    """Main order request that groups quotations with same origin/destination/dates"""
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='order_requests',
        limit_choices_to={'role': 'customer'}
    )
    
    # Unique identifier for grouping quotations
    origin_pincode = models.CharField(max_length=10)
    destination_pincode = models.CharField(max_length=10)
    pickup_date = models.DateTimeField()
    drop_date = models.DateTimeField()
    
    # Additional trip details
    weight = models.DecimalField(max_digits=8, decimal_places=2, help_text="Weight in tonnes")
    weight_unit = models.CharField(max_length=10, default='tonnes')
    urgency_level = models.CharField(max_length=20, default='standard')
    
    # Status tracking
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active - Collecting Quotes'),
        ('confirmed', 'Order Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_active = models.BooleanField(default=True)
    
    # Confirmed quotation (when order is finalized)
    confirmed_quotation = models.ForeignKey(
        'Quotation', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='confirmed_orders'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['customer', 'origin_pincode', 'destination_pincode', 'pickup_date', 'drop_date']
        ordering = ['-created_at']

    def __str__(self):
        return f"Order Request {self.id}: {self.origin_pincode} → {self.destination_pincode} ({self.customer.name})"

    def deactivate_on_confirmation(self):
        """Deactivate order request when an order is confirmed"""
        self.status = 'confirmed'
        self.is_active = False
        self.save()

class QuotationRequest(models.Model):
    """Individual quotation request linked to an OrderRequest"""
    order_request = models.ForeignKey(
        OrderRequest,
        on_delete=models.CASCADE,
        related_name='quotation_requests'
    )
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_quotation_requests',
        limit_choices_to={'role': 'vendor'}
    )
    
    # Frontend data from searchParams
    origin_location = models.CharField(max_length=100, blank=True)
    destination_location = models.CharField(max_length=100, blank=True)
    vehicle_type = models.CharField(max_length=50, null=True, blank=True)
    
    # Request details (will be filled from order_request mostly)
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_address = models.TextField(blank=True)
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_address = models.TextField(blank=True)
    
    # Additional details
    cargo_description = models.TextField(blank=True)
    special_instructions = models.TextField(blank=True)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['order_request', 'vendor']

    def __str__(self):
        return f"Quote Request {self.id} for Order {self.order_request.id} to {self.vendor.name}"

    @property
    def customer(self):
        return self.order_request.customer
    
    @property
    def pickup_date(self):
        return self.order_request.pickup_date
    
    @property
    def expected_delivery_date(self):
        return self.order_request.drop_date
    
    @property
    def estimated_total_weight(self):
        return self.order_request.weight

class Quotation(models.Model):
    """Vendor's quotation for an OrderRequest"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent to Customer'),
        ('negotiating', 'Under Negotiation'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    order_request = models.ForeignKey(
        OrderRequest, 
        on_delete=models.CASCADE, 
        related_name='quotations'
    )
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quotations',
        limit_choices_to={'role': 'vendor'}
    )
    
    # Frontend data
    vendor_id = models.CharField(max_length=100, blank=True, help_text="Frontend vendor ID")
    vendor_name = models.CharField(max_length=200, blank=True, help_text="Frontend vendor name")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Detailed pricing
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fuel_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    toll_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    loading_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unloading_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    additional_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Terms
    terms_and_conditions = models.TextField(blank=True)
    validity_hours = models.PositiveIntegerField(default=24, help_text="Quote validity in hours")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['order_request', 'vendor']

    def __str__(self):
        return f"Quotation {self.id} - ₹{self.total_amount} by {self.vendor.name}"

    @property
    def customer(self):
        return self.order_request.customer

class QuotationItem(models.Model):
    """Items in a quotation from frontend"""
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    
    # Item data from frontend
    item_data = models.JSONField(help_text="Raw item data from frontend")
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Item for Quotation {self.quotation.id}"

class QuotationItem(models.Model):
    """Individual truck pricing in a quotation"""
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    
    # Per-truck pricing
    unit_base_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Base price per truck")
    unit_fuel_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_toll_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_loading_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_unloading_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_additional_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Calculated totals for this truck type
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Item-specific terms
    item_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['quotation', 'truck']

    def __str__(self):
        return f"{self.quantity}x {self.truck.registration_number} - ₹{self.total_price}"

    def save(self, *args, **kwargs):
        """Calculate total price for this item"""
        unit_total = (
            self.unit_base_price + self.unit_fuel_charges + self.unit_toll_charges +
            self.unit_loading_charges + self.unit_unloading_charges + self.unit_additional_charges
        )
        self.total_price = unit_total * self.quantity
        super().save(*args, **kwargs)

class QuotationNegotiation(models.Model):
    """Track negotiation history between customer and vendor"""
    INITIATOR_CHOICES = [
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
    ]

    quotation = models.ForeignKey(
        Quotation, 
        on_delete=models.CASCADE, 
        related_name='negotiations'
    )
    initiated_by = models.CharField(max_length=10, choices=INITIATOR_CHOICES)
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

class QuotationRequestItem(models.Model):
    """Individual truck items in a quotation request (like cart items)"""
    quotation_request = models.ForeignKey(
        QuotationRequest, 
        on_delete=models.CASCADE, 
        related_name='items'
    )
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, help_text="Number of trucks of this type needed")
    
    # Item-specific details
    item_weight = models.DecimalField(max_digits=8, decimal_places=2, help_text="Weight for this truck type in tons")
    item_special_instructions = models.TextField(blank=True, help_text="Special instructions for this truck type")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['quotation_request', 'truck']

    def __str__(self):
        return f"{self.quantity}x {self.truck.registration_number} for Request {self.quotation_request.id}"

    def get_total_capacity(self):
        """Get total capacity for this item"""
        return self.truck.capacity * self.quantity

class Cart(models.Model):
    """Temporary cart for customers before creating quotation request"""
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='carts',
        limit_choices_to={'role': 'customer'}
    )
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='customer_carts',
        limit_choices_to={'role': 'vendor'}
    )
    
    # Cart will be cleared after quotation request is created
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['customer', 'vendor']  # One cart per vendor per customer

    def __str__(self):
        return f"Cart for {self.customer.name} with {self.vendor.name}"

    def get_total_trucks(self):
        """Get total number of trucks in cart"""
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0

    def get_total_capacity(self):
        """Get total capacity of all trucks in cart"""
        total = 0
        for item in self.items.all():
            total += item.truck.capacity * item.quantity
        return total

    def clear(self):
        """Clear all items from cart"""
        self.items.all().delete()

class CartItem(models.Model):
    """Individual truck items in customer's cart"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    
    # Item-specific requirements
    item_weight = models.DecimalField(max_digits=8, decimal_places=2, help_text="Weight for this truck type in tons")
    item_special_instructions = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['cart', 'truck']

    def __str__(self):
        return f"{self.quantity}x {self.truck.registration_number} in {self.cart.customer.name}'s cart"

    def get_total_capacity(self):
        """Get total capacity for this cart item"""
        return self.truck.capacity * self.quantity

    def get_estimated_price(self):
        """Get estimated price for this cart item based on truck's base price"""
        # This is just an estimate, actual pricing comes from vendor quotation
        return self.truck.base_price_per_km * self.quantity

# ============ ROUTE-BASED PRICING MODELS ============

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
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_address = models.TextField()
    pickup_city = models.CharField(max_length=100)
    pickup_state = models.CharField(max_length=100)
    pickup_pincode = models.CharField(max_length=10, null=True, blank=True, help_text="Pickup pincode")
    pickup_date = models.DateTimeField()
    
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6)
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

class VendorEnquiryRequest(models.Model):
    """Manager's request to vendors for specific enquiry"""
    REQUEST_STATUS_CHOICES = [
        ('sent', 'Sent to Vendor'),
        ('viewed', 'Viewed by Vendor'),
        ('quoted', 'Vendor Quoted'),
        ('accepted', 'Vendor Accepted'),
        ('rejected', 'Vendor Rejected'),
        ('expired', 'Expired'),
    ]
    
    enquiry = models.ForeignKey(CustomerEnquiry, on_delete=models.CASCADE, related_name='vendor_requests')
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_enquiry_requests',
        limit_choices_to={'role': 'vendor'}
    )
    price_range = models.ForeignKey(PriceRange, on_delete=models.CASCADE)
    route = models.ForeignKey(Route, on_delete=models.CASCADE, null=True, blank=True)
    
    # Manager details
    sent_by_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_vendor_requests',
        limit_choices_to={'role': 'manager'}
    )
    
    # Request details
    suggested_price = models.DecimalField(max_digits=10, decimal_places=2)
    manager_notes = models.TextField(blank=True)
    urgency_level = models.CharField(max_length=10, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], default='medium')
    
    # Response tracking
    status = models.CharField(max_length=20, choices=REQUEST_STATUS_CHOICES, default='sent')
    vendor_response_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    vendor_response_notes = models.TextField(blank=True)
    response_date = models.DateTimeField(null=True, blank=True)
    
    # Validity
    valid_until = models.DateTimeField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['enquiry', 'vendor', 'price_range']
        ordering = ['-created_at']

    def __str__(self):
        return f"Request to {self.vendor.name} for Enquiry {self.enquiry.id}"
