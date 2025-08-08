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

### Role-Based Permissions
Custom permission classes are defined in each app's views.py:
```python
class IsVendor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'vendor'
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

## Database Schema & Relationships

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
Route (∞) ←→ (∞) CustomerEnquiry (matched_routes)

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

### Key Models & Fields

#### Authentication App
- **CustomUser**: `email` (USERNAME_FIELD), `phone_number`, `role` (customer/vendor/manager/admin), `name`
- **OTP**: `phone_number`, `otp`, `is_verified`, `created_at`

#### Trucks App
- **TruckType**: `name`, `description`
- **Truck**: `vendor` (FK), `truck_type` (FK), `registration_number` (unique), `capacity`, `make`, `model`, `availability_status`, `current_location_*`
- **Driver**: `vendor` (FK), `name`, `license_number` (unique), `assigned_truck` (FK optional), `is_available`
- **TruckImage**: `truck` (FK), `image`, `is_primary`
- **TruckDocument**: `truck` (FK), `document_type`, `document_file`, `expiry_date`
- **TruckLocation**: `truck` (FK), `latitude`, `longitude`, `timestamp`

#### Quotations App
- **Route**: `vendor` (FK), `route_name`, `origin_*`, `destination_*`, `total_distance_km`, `route_frequency`
- **RouteStop**: `route` (FK), `stop_city`, `stop_order`, `distance_from_origin`, `can_pickup`, `can_drop`
- **RoutePricing**: `route` (FK), `truck_type` (FK), `from_city`, `to_city`, `segment_distance_km`, `base_price`, `price_per_km`
- **CustomerEnquiry**: `customer` (FK), `assigned_manager` (FK), `pickup_*`, `delivery_*`, `truck_type` (FK), `matched_routes` (M2M)
- **QuotationRequest**: `customer` (FK), `vendor` (FK), `pickup_*`, `delivery_*`, `estimated_total_weight`
- **Quotation**: `quotation_request` (FK), `vendor` (FK), `total_amount`, `status`, `validity_hours`

#### Orders App
- **Order**: `quotation` (1-to-1), `customer` (FK), `vendor` (FK), `truck` (FK), `driver` (FK), `order_number` (unique), `status`, `total_amount`
- **OrderStatusHistory**: `order` (FK), `previous_status`, `new_status`, `updated_by` (FK), `timestamp`
- **OrderTracking**: `order` (FK), `latitude`, `longitude`, `speed`, `heading`, `timestamp`
- **OrderDocument**: `order` (FK), `document_type`, `file`, `uploaded_by` (FK)

#### Payments App
- **Payment**: `order` (FK), `payment_id` (unique), `amount`, `payment_type`, `payment_method`, `status`, `gateway_transaction_id`
- **Invoice**: `order` (FK), `vendor` (FK), `invoice_number` (unique), `amount`, `pdf_file`
- **PaymentHistory**: `payment` (FK), `previous_status`, `new_status`, `timestamp`

### Critical Constraints
- **Unique Together**: Route (vendor, origin_city, destination_city), RoutePricing (route, truck_type, from_city, to_city)
- **Role Limitations**: All foreign keys to CustomUser have `limit_choices_to={'role': 'specific_role'}`
- **Cascade Behaviors**: Most relationships cascade on delete except driver assignments (SET_NULL)

## Key Files for Context

- `project/utils.py` - Response standardization (READ FIRST)
- `trucks/api/views.py::truck_search()` - Complex search algorithm
- `quotations/models.py` - Route and pricing models
- `authentication/models.py` - CustomUser with role system
- `API_DOCUMENTATION.md` - Complete API reference

## Common Gotchas

1. **Always use trailing slashes** in URL patterns to avoid 301 redirects
2. **CustomUser has no username field** - use `email` or `name` for logging
3. **Route pricing requires segment_distance_km** - calculate using haversine formula
4. **Truck deduplication** needed when same truck serves multiple routes
5. **Manager role** is central to workflow - don't create direct customer-vendor APIs

## Testing Credentials (from sample data)
- Vendor: `vendor1@truckrent.com` / `vendor123`
- Customer: `customer1@example.com` / `customer123`  
- Test pincodes: Mumbai(400001), Delhi(110001), Bangalore(560001), Chennai(600001)
