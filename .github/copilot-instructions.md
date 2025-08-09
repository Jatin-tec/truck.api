# Truck Rental Platform - AI Coding Agent Instructions

## Project Architecture Overview

This is a Django REST Framework-based "Uber for Transport" platform with a unique **manager-mediated workflow**. Unlike direct customer-vendor interactions, this system uses managers to coordinate between customers seeking transport and vendors offering trucks.

### Core Business Model
- **Customers** submit enquiries (not direct truck requests)
- **Managers** mediate all vendor-customer communication  
- **Vendors** define routes and respond through managers
- Price ranges shown to customers, not individual vendor details
- Both parties must confirm through manager before order creation

## App Structure & Boundaries

- **authentication/**: CustomUser model with roles (customer, vendor, manager, admin). Uses email as USERNAME_FIELD, supports OTP verification
- **trucks/**: Truck/Driver management + advanced search with route-based matching via haversine distance calculations
- **quotations/**: Complex enquiry system with Route/RouteStop/RoutePricing models for vendor route definitions
- **orders/**: Order lifecycle management (created → pickup → shipped → arrived)
- **payments/**: Payment processing with invoice generation

## 🔧 REUSABLE MODULES & COMPONENTS

### Core Utility Modules

#### 1. **Response Standardization** (`project/utils.py`)
**CRITICAL**: All views MUST use standardized responses
```python
# Functions
- create_standardized_response()
- success_response()
- error_response()
- validation_error_response()

# Classes
- StandardizedAPIView (base for APIView)
- StandardizedResponseMixin (mixin for DRF generic views)

# Standard Format:
{
  "success": boolean,
  "data": any,
  "message": string,
  "error": string,
  "errors": {"field": ["error1", "error2"]}
}
```

#### 2. **Location Services** (`project/location_utils.py`)
```python
# Functions
- validate_pincode(pincode: str) -> bool
- get_coordinates_from_pincode(pincode: str) -> Tuple[float, float]
- calculate_distance(lat1, lon1, lat2, lon2) -> float  # Haversine formula
- find_nearest_location(target_lat, target_lon, locations, max_distance=50) -> list
- get_city_from_pincode(pincode: str) -> str

# Mock Pincode Data for Major Cities:
- Mumbai: 400001, Delhi: 110001, Bangalore: 560001, Chennai: 600001
- Kolkata: 700001, Hyderabad: 500001, Pune: 411001, Ahmedabad: 380001
```

#### 3. **Authentication System** (`authentication/`)
```python
# CustomUserManager
- create_user(email/phone_number, password, **extra_fields)
- create_superuser(email, password, **extra_fields)

# Custom Backend (authentication_backends.py)
- EmailOrPhoneBackend: Supports login with email OR phone number

# OTP System
- OTP model with phone_number, otp, is_verified, expiry logic
- is_expired() method (10-minute validity)
```

### Role-Based Permission Classes

**✅ CENTRALIZED & IMPLEMENTED**: All permission classes are now centralized in `project/permissions.py`

#### Available Centralized Permissions
```python
from project.permissions import (
    IsCustomer, IsVendor, IsManager, IsAdmin,
    IsCustomerOrVendor, IsVendorOrManager, IsCustomerOrManager,
    IsVendorOrReadOnly, IsOwnerOrReadOnly, 
    IsVendorOwnerOrReadOnly, IsCustomerOwnerOrReadOnly
)
```

#### Key Permission Classes:
- **IsVendorOrReadOnly**: Enhanced with object-level permissions for vendor ownership
- **IsOwnerOrReadOnly**: Generic ownership validation for multiple field names
- **Role-specific**: IsCustomer, IsVendor, IsManager, IsAdmin
- **Combined roles**: IsCustomerOrVendor, IsVendorOrManager, etc.

### Data Management Commands

#### Sample Data Generation (`trucks/management/commands/create_sample_data.py`)
```bash
python manage.py create_sample_data --clear
```
- Creates comprehensive test data
- Realistic routes between major Indian cities
- User accounts for all roles
- Truck types and pricing data

## Critical Code Patterns

### Standardized API Responses
All views MUST inherit from `StandardizedAPIView` or use `StandardizedResponseMixin`:
```python
# From project/utils.py - ALWAYS use this format
{
  "success": boolean,
  "data": any,
  "message": string,
  "error": string,
  "errors": {"field": ["error1", "error2"]}
}
```

### Route-Based Truck Search
Complex algorithm in `trucks/api/views.py::truck_search()`:
- Converts pincodes to coordinates using `project/location_utils.py`
- Matches pickup/delivery points to vendor routes with tolerance radius
- Deduplicates trucks across multiple routes (keeps best price)
- Key files: `quotations/models.py` (Route, RouteStop, RoutePricing)

## Development Workflows

### Sample Data Creation
```bash
python manage.py create_sample_data --clear
```
Creates comprehensive test data with routes between major Indian cities, realistic pricing, and user accounts.

### Key Commands
- `python manage.py migrate` - Apply database changes
- `python manage.py runserver` - Start development server
- All API endpoints documented in `API_DOCUMENTATION.md`

## Model Relationships (Critical)

### Route System
```
Vendor → Route → RouteStop (intermediate cities)
Route → RoutePricing (per truck type pricing)
```

### Enquiry Flow
```
Customer → CustomerEnquiry → Manager assigns → VendorEnquiryRequest → Order
```

### User Authentication
- Uses JWT tokens (SimpleJWT)
- Custom authentication backend supports email OR phone login
- Settings: `AUTH_USER_MODEL = 'authentication.CustomUser'`

## Integration Points

### Location Services
- `project/location_utils.py` handles pincode-to-coordinates conversion
- Haversine distance calculations for route matching
- Support for both pincode and lat/lng inputs

### Database Configuration
- Supports PostgreSQL (production) and SQLite (development)
- Environment-based configuration in `project/settings.py`
- Redis caching configured

## 🗃️ DATABASE SCHEMA & RELATIONSHIPS

### Core Entity Relationships
```
CustomUser (1) ←→ (∞) Truck (vendor role)
CustomUser (1) ←→ (∞) Driver (vendor role)
CustomUser (1) ←→ (∞) Route (vendor role)
CustomUser (1) ←→ (∞) CustomerEnquiry (customer role)
CustomUser (1) ←→ (∞) Order (customer/vendor roles)

TruckType (1) ←→ (∞) Truck
TruckType (1) ←→ (∞) RoutePricing

Route (1) ←→ (∞) RouteStop
Route (1) ←→ (∞) RoutePricing
Route (∞) ←→ (∞) CustomerEnquiry (matched_routes M2M)

QuotationRequest (1) ←→ (∞) Quotation
Quotation (1) ←→ (1) Order
Order (1) ←→ (∞) OrderStatusHistory
Order (1) ←→ (∞) OrderTracking
Order (1) ←→ (∞) OrderDocument
Order (1) ←→ (∞) Payment

Truck (1) ←→ (∞) TruckImage
Truck (1) ←→ (∞) TruckDocument
Truck (1) ←→ (∞) TruckLocation
Truck (1) ←→ (1) Driver (optional assignment)
```

### 📊 COMPLETE MODEL SCHEMAS

#### Authentication App Models

**CustomUser** (AUTH_USER_MODEL)
```python
Fields:
- id: AutoField (PK)
- email: EmailField (unique, USERNAME_FIELD)
- name: CharField(100)
- phone_number: CharField(15, unique)
- dob: DateField
- role: CharField(choices=['admin', 'customer', 'vendor', 'manager'])
- is_active: BooleanField(default=True)
- is_staff: BooleanField(default=False)
- created_at, updated_at: DateTimeField

Methods:
- get_full_name(): Returns alphanumeric name
- get_user_id(): Returns formatted ID with role
```

**OTP**
```python
Fields:
- phone_number: CharField(15)
- otp: CharField(6)
- created_at: DateTimeField
- is_verified: BooleanField(default=False)

Methods:
- is_expired(): Checks 10-minute validity
```

#### Trucks App Models

**TruckType**
```python
Fields:
- name: CharField(50, unique)  # "Mini Truck", "Large Truck", "Container"
- description: TextField
- created_at, updated_at: DateTimeField
```

**Truck**
```python
Fields:
- vendor: FK(CustomUser, role='vendor')
- truck_type: FK(TruckType)
- registration_number: CharField(20, unique)
- capacity: DecimalField  # in tons
- make, model: CharField(50)
- year: PositiveIntegerField(1990-2030)
- color: CharField(30)
- availability_status: CharField(choices=['available', 'busy', 'maintenance', 'inactive'])
- base_price_per_km: DecimalField

# Location fields
- current_location_latitude, longitude: DecimalField
- current_location_address: TextField

# Metadata
- is_active: BooleanField(default=True)
- created_at, updated_at: DateTimeField
```

**Driver**
```python
Fields:
- vendor: FK(CustomUser, role='vendor')
- name: CharField(100)
- phone_number: CharField(15)
- email: EmailField
- license_number: CharField(50, unique)
- license_expiry_date: DateField
- experience_years: PositiveIntegerField
- assigned_truck: FK(Truck, SET_NULL, optional)
- license_image, profile_image: ImageField
- is_available, is_active: BooleanField
- created_at, updated_at: DateTimeField
```

**TruckDocument**
```python
Fields:
- truck: FK(Truck)
- document_type: CharField(50)  # "RC", "Insurance", "Fitness Certificate"
- document_file: FileField
- expiry_date: DateField
- is_active: BooleanField
- created_at, updated_at: DateTimeField
```

**TruckImage**
```python
Fields:
- truck: FK(Truck)
- image: ImageField
- caption: CharField(100)
- is_primary: BooleanField
- created_at: DateTimeField
```

**TruckLocation**
```python
Fields:
- truck: FK(Truck)
- latitude, longitude: DecimalField
- address: TextField
- timestamp: DateTimeField
```

#### Quotations App Models

**Route**
```python
Fields:
- vendor: FK(CustomUser, role='vendor')
- route_name: CharField(200)
- origin_city, origin_state: CharField(100)
- origin_pincode: CharField(10)
- origin_latitude, origin_longitude: DecimalField
- destination_city, destination_state: CharField(100)
- destination_pincode: CharField(10)
- destination_latitude, destination_longitude: DecimalField
- total_distance_km: DecimalField
- estimated_duration_hours: DecimalField
- route_frequency: CharField(choices=['daily', 'weekly', 'biweekly', 'monthly', 'on_demand'])
- is_active: BooleanField
- max_vehicles_per_trip: PositiveIntegerField
- notes: TextField
- created_at, updated_at: DateTimeField

Constraints:
- unique_together: ['vendor', 'origin_city', 'destination_city']
```

**RouteStop**
```python
Fields:
- route: FK(Route)
- stop_city, stop_state: CharField(100)
- stop_pincode: CharField(10)
- stop_latitude, stop_longitude: DecimalField
- stop_order: PositiveIntegerField
- distance_from_origin, distance_to_destination: DecimalField
- estimated_arrival_time: DecimalField  # hours from origin
- can_pickup, can_drop: BooleanField
- created_at: DateTimeField

Constraints:
- unique_together: ['route', 'stop_order']
```

**RoutePricing**
```python
Fields:
- route: FK(Route)
- truck_type: FK(TruckType)
- from_city, to_city: CharField(100)
- segment_distance_km: DecimalField
- base_price, price_per_km: DecimalField
- fuel_charges, toll_charges: DecimalField
- loading_charges, unloading_charges: DecimalField
- min_price, max_price: DecimalField
- max_weight_capacity: DecimalField
- available_vehicles: PositiveIntegerField
- is_active: BooleanField
- last_updated, created_at: DateTimeField

Methods:
- get_total_price(): Sum of all charges

Constraints:
- unique_together: ['route', 'truck_type', 'from_city', 'to_city']
```

**CustomerEnquiry**
```python
Fields:
- customer: FK(CustomUser, role='customer')
- pickup_latitude, pickup_longitude: DecimalField(default=0.0)
- pickup_address: TextField
- pickup_city, pickup_state: CharField(100)
- pickup_pincode: CharField(10)
- pickup_date: DateTimeField
- delivery_latitude, delivery_longitude: DecimalField(default=0.0)
- delivery_address: TextField
- delivery_city, delivery_state: CharField(100)
- delivery_pincode: CharField(10)
- expected_delivery_date: DateTimeField
- truck_type: FK(TruckType)
- number_of_vehicles: PositiveIntegerField(default=1)
- total_weight: DecimalField
- cargo_description: TextField
- special_instructions: TextField
- estimated_distance_km: DecimalField
- matched_routes: M2M(Route)
- is_miscellaneous_route: BooleanField
- status: CharField(choices=['submitted', 'under_review', 'quotes_generated', etc.])
- assigned_manager: FK(CustomUser, role='manager', SET_NULL)
- budget_min, budget_max: DecimalField
- preferred_vendor_size: CharField(choices=['small', 'medium', 'large', 'any'])
- created_at, updated_at: DateTimeField
```

**QuotationRequest**
```python
Fields:
- customer: FK(CustomUser, role='customer')
- origin_pincode, destination_pincode: CharField(10)
- pickup_date, drop_date: DateField
- weight: DecimalField
- weight_unit: CharField(choices=['kg', 'ton', 'lbs'])
- vehicle_type: CharField(50)
- urgency_level: CharField(choices=['low', 'medium', 'high', 'urgent'])
- pickup_latitude, pickup_longitude: DecimalField
- pickup_address: TextField
- delivery_latitude, delivery_longitude: DecimalField
- delivery_address: TextField
- cargo_description, special_instructions: TextField
- distance_km: DecimalField
- is_active: BooleanField
- created_at, updated_at: DateTimeField

Constraints:
- unique_together: ['customer', 'origin_pincode', 'destination_pincode', 'pickup_date', 'drop_date']
```

**Quotation**
```python
Fields:
- quotation_request: FK(QuotationRequest)
- vendor: FK(CustomUser, role='vendor')
- vendor_name: CharField(200)
- items: JSONField  # List of vehicle items
- total_amount: DecimalField
- terms_and_conditions: TextField
- validity_hours: PositiveIntegerField(default=24)
- customer_suggested_price: DecimalField
- vendor_response_to_suggestion: TextField
- status: CharField(choices=['pending', 'sent', 'negotiating', 'accepted', 'rejected', 'expired'])
- is_active: BooleanField
- created_at, updated_at: DateTimeField

Constraints:
- unique_together: ['quotation_request', 'vendor']
```

**PriceRange**
```python
Fields:
- enquiry: FK(CustomerEnquiry)
- min_price, max_price, recommended_price: DecimalField
- vehicles_available, vendors_count: PositiveIntegerField
- chance_of_getting_deal: CharField(choices=['low', 'medium', 'high'])
- route_type: CharField(choices=['direct', 'via_stops', 'miscellaneous'])
- estimated_duration_hours: DecimalField
- supporting_routes: M2M(Route)
- includes_fuel, includes_tolls, includes_loading: BooleanField
- additional_charges_note: TextField
- created_at: DateTimeField
```

**VendorEnquiryRequest**
```python
Fields:
- enquiry: FK(CustomerEnquiry)
- vendor: FK(CustomUser, role='vendor')
- price_range: FK(PriceRange)
- route: FK(Route)
- sent_by_manager: FK(CustomUser, role='manager')
- suggested_price: DecimalField
- manager_notes: TextField
- urgency_level: CharField(choices=['low', 'medium', 'high', 'urgent'])
- status: CharField(choices=['sent', 'viewed', 'quoted', 'accepted', 'rejected', 'expired'])
- vendor_response_price: DecimalField
- vendor_response_notes: TextField
- response_date: DateTimeField
- valid_until: DateTimeField
- created_at, updated_at: DateTimeField

Constraints:
- unique_together: ['enquiry', 'vendor', 'price_range']
```

#### Orders App Models

**Order**
```python
Fields:
- order_number: CharField(20, unique)
- quotation: OneToOneField(Quotation)
- customer: FK(CustomUser, role='customer')
- vendor: FK(CustomUser, role='vendor')
- truck: FK(Truck)
- driver: FK(Driver, SET_NULL)
- pickup_address, delivery_address: TextField
- pickup_latitude, pickup_longitude: DecimalField
- delivery_latitude, delivery_longitude: DecimalField
- scheduled_pickup_date, scheduled_delivery_date: DateTimeField
- actual_pickup_date, actual_delivery_date: DateTimeField
- total_amount: DecimalField
- cargo_description: TextField
- estimated_weight, actual_weight: DecimalField
- status: CharField(choices=['created', 'confirmed', 'driver_assigned', 'pickup', 'picked_up', 'in_transit', 'delivered', 'completed', 'cancelled'])
- special_instructions, delivery_instructions: TextField
- delivery_otp: CharField(6)
- is_otp_verified: BooleanField
- is_active: BooleanField
- created_at, updated_at: DateTimeField

Auto-generation:
- order_number: "ORD{timestamp}" format
```

**OrderStatusHistory**
```python
Fields:
- order: FK(Order)
- previous_status, new_status: CharField(20)
- updated_by: FK(CustomUser)
- notes: TextField
- location_latitude, location_longitude: DecimalField
- timestamp: DateTimeField
```

**OrderTracking**
```python
Fields:
- order: FK(Order)
- latitude, longitude: DecimalField
- address: TextField
- speed: DecimalField  # km/h
- heading: DecimalField  # degrees
- timestamp: DateTimeField
```

**OrderDocument**
```python
Fields:
- order: FK(Order)
- document_type: CharField(choices=['pickup_receipt', 'delivery_receipt', 'cargo_photo', 'damage_report', 'invoice', 'other'])
- file: FileField
- description: CharField(200)
- uploaded_by: FK(CustomUser)
- uploaded_at: DateTimeField
```

#### Payments App Models

**Payment**
```python
Fields:
- payment_id: CharField(50, unique)
- order: FK(Order)
- amount: DecimalField
- payment_type: CharField(choices=['advance', 'full', 'balance'])
- payment_method: CharField(choices=['card', 'upi', 'netbanking', 'wallet', 'cash', 'bank_transfer'])
- gateway_transaction_id: CharField(100)
- gateway_name: CharField(50)
- gateway_response: JSONField
- status: CharField(choices=['pending', 'initiated', 'processing', 'completed', 'failed', 'cancelled', 'refunded'])
- initiated_at, completed_at, failed_at: DateTimeField
- notes, failure_reason: TextField
- created_at, updated_at: DateTimeField

Auto-generation:
- payment_id: "PAY{timestamp}{order_id}" format
```

**Invoice**
```python
Fields:
- invoice_number: CharField(30, unique)
- order: OneToOneField(Order)
- subtotal, tax_amount, discount_amount, total_amount: DecimalField
- base_charges, fuel_charges, toll_charges: DecimalField
- loading_charges, unloading_charges, additional_charges: DecimalField
- cgst_rate, sgst_rate, igst_rate: DecimalField
- cgst_amount, sgst_amount, igst_amount: DecimalField
- invoice_file: FileField
- is_generated: BooleanField
- generated_at: DateTimeField
- created_at, updated_at: DateTimeField

Auto-generation:
- invoice_number: "INV{YYYYMMDD}{counter}" format
- Auto-calculates totals on save()
```

**PaymentHistory**
```python
Fields:
- payment: FK(Payment)
- previous_status, new_status: CharField(20)
- notes: TextField
- timestamp: DateTimeField
```

### Critical Constraints & Business Rules
- **Unique Together Constraints**: Route (vendor, origin_city, destination_city), RoutePricing (route, truck_type, from_city, to_city), CustomerEnquiry (customer, origin_pincode, destination_pincode, pickup_date, drop_date)
- **Role Limitations**: All foreign keys to CustomUser have `limit_choices_to={'role': 'specific_role'}`
- **Cascade Behaviors**: Most relationships cascade on delete except driver assignments (SET_NULL)
- **Auto-Generation**: Order numbers, payment IDs, invoice numbers auto-generate with timestamps
- **Location Fields**: All models with location use DecimalField(max_digits=9, decimal_places=6)

## 🚨 REDUNDANCY & CLEANUP ISSUES IDENTIFIED

### Files to Remove/Consolidate
1. **`quotations/route_models.py`** - DUPLICATE of models in `quotations/models.py`
2. **`quotations/models_new.py`** - EMPTY FILE to delete
3. **Permission Classes** - Scattered across apps, need centralization

### Inconsistencies Found
1. **CustomerEnquiry Model**: Some location fields have `default=0.0`, others don't
2. **Quotation Model**: Has duplicate fields and save method issues
3. **Permission Classes**: Same classes defined in multiple files

## 🔧 RECOMMENDED CLEANUP ACTIONS

### 1. Create Centralized Permissions (`project/permissions.py`)
Move all permission classes to a single file to avoid duplication across:
- `trucks/api/views.py`
- `orders/api/views.py` 
- `payments/api/views.py`
- `quotations/helper.py`

### 2. Remove Redundant Files
- Delete `quotations/route_models.py` (exact duplicate)
- Delete `quotations/models_new.py` (empty)
- Update imports to use centralized permissions

### 3. Fix Model Inconsistencies
- Standardize location field defaults in CustomerEnquiry
- Remove duplicate Quotation save method
- Ensure consistent field naming patterns

## Key Files for Context

- `project/utils.py` - Response standardization (READ FIRST)
- `project/location_utils.py` - Location utilities
- `project/permissions.py` - Centralized permission classes (USE THESE!)
- `authentication/authentication_backends.py` - Custom auth backend
- `trucks/api/views.py::truck_search()` - Complex search algorithm
- `quotations/models.py` - Route and pricing models (ACTIVE - cleaned up)
- `authentication/models.py` - CustomUser with role system
- `trucks/management/commands/create_sample_data.py` - Sample data creation
- `API_DOCUMENTATION.md` - Complete API reference
- `CLEANUP_TODO.md` - Pending cleanup actions and improvements

## Common Gotchas

1. **Always use trailing slashes** in URL patterns to avoid 301 redirects
2. **CustomUser has no username field** - use `email` or `name` for logging
3. **Route pricing requires segment_distance_km** - calculate using haversine formula
4. **Truck deduplication** needed when same truck serves multiple routes
5. **Manager role** is central to workflow - don't create direct customer-vendor APIs
6. **Use centralized permissions** - Import from `project.permissions` ✅ COMPLETED
7. **Quotation model** - No auto-calculation save method, total_amount must be set explicitly

## 🔧 IMMEDIATE ACTION REQUIRED

~~**Replace scattered permission classes** with centralized ones from `project.permissions`:~~ ✅ COMPLETED
- ~~`trucks/api/views.py` - Replace IsVendor, IsVendorOrReadOnly~~  
- ~~`orders/api/views.py` - Replace IsCustomer, IsVendor, IsCustomerOrVendor~~
- ~~`payments/api/views.py` - Replace IsCustomer, IsVendor, IsCustomerOrVendor~~
- ~~`quotations/helper.py` - Replace IsCustomer, IsVendor, IsCustomerOrVendor~~

**Current Status**: ✅ All permission classes have been centralized and migrated successfully.

See `CLEANUP_TODO.md` for remaining cleanup tasks (model standardization and architectural improvements).

## Testing Credentials (from sample data)
- Vendor: `vendor1@truckrent.com` / `vendor123`
- Customer: `customer1@example.com` / `customer123`  
- Test pincodes: Mumbai(400001), Delhi(110001), Bangalore(560001), Chennai(600001)
