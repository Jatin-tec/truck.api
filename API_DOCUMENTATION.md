# 🚚 Tracking Trucks - API Documentation

## 📚 Complete API Reference

This is a comprehensive truck rental platform API built with Django REST Framework. The system transforms the traditional "Uber for Transport" model into a **"Tracking Trucks"** platform with a manager-mediated workflow that provides customers with price ranges without exposing vendor details.

## 🛒 Key Features

### **Customer Enquiry System**
- Customers submit enquiries with pickup/drop locations, dates, vehicle types, and load details
- System returns price ranges (not vendor details), number of vehicles available, and deal probability
- No direct vendor exposure until price range selection

### **Manager-Mediated Workflow**
- New "manager" role mediates all communication between customers and vendors
- Managers handle enquiry distribution to appropriate vendors
- Both vendor and customer must confirm through manager before order creation

### **Route-Based Pricing**
- Vendors define regular routes with fixed price ranges
- Support for miscellaneous (non-regular) routes with estimated pricing
- Automatic route matching for accurate pricing

## 🔐 Authentication

All authenticated endpoints require JWT token in the Authorization header:
```
Authorization: Bearer <access_token>
```

### User Roles
- **Customer**: Submit enquiries, select price ranges, confirm orders
- **Vendor**: Define routes, respond to enquiries, manage trucks
- **Manager**: Mediate between customers and vendors, manage enquiries

### Authentication Endpoints

```
POST /api/auth/login/                    # Login with email/password
POST /api/auth/send-otp/                 # Send OTP to phone number
POST /api/auth/verify-otp/               # Verify OTP and get tokens
POST /api/auth/token/refresh/            # Refresh access token
POST /api/auth/update-user/              # Update user profile
GET  /api/auth/get-user/                 # Get current user info
```

## 🎯 Customer Enquiry APIs

### Customer Enquiry Flow

```
POST /api/quotations/enquiries/          # Submit customer enquiry
GET  /api/quotations/enquiries/          # List customer's enquiries
GET  /api/quotations/enquiries/{id}/     # Get enquiry details
POST /api/quotations/enquiries/{id}/select-price-range/  # Select price range
POST /api/quotations/enquiries/{id}/confirm/  # Confirm order after vendor acceptance
```

#### Submit Customer Enquiry
```json
POST /api/quotations/enquiries/
{
  "pickup_latitude": 19.0760,
  "pickup_longitude": 72.8777,
  "pickup_address": "Mumbai, Maharashtra",
  "pickup_date": "2025-07-15T10:00:00Z",
  "delivery_latitude": 28.7041,
  "delivery_longitude": 77.1025,
  "delivery_address": "Delhi",
  "delivery_date": "2025-07-15T18:00:00Z",
  "truck_type": "Medium",
  "load_description": "Electronics goods",
  "estimated_weight": 5.0,
  "number_of_vehicles": 2,
  "special_instructions": "Handle with care"
}
```

#### Enquiry Response with Price Ranges
```json
{
  "id": 1,
  "pickup_address": "Mumbai, Maharashtra",
  "delivery_address": "Delhi",
  "pickup_date": "2025-07-15T10:00:00Z",
  "delivery_date": "2025-07-15T18:00:00Z",
  "truck_type": "Medium",
  "load_description": "Electronics goods",
  "estimated_weight": 5.0,
  "number_of_vehicles": 2,
  "status": "pending_price_selection",
  "price_ranges": [
    {
      "id": 1,
      "min_price": 2500.00,
      "max_price": 3000.00,
      "estimated_price": 2750.00,
      "available_vehicles": 5,
      "deal_probability": 85
    },
    {
      "id": 2,
      "min_price": 3000.00,
      "max_price": 3500.00,
      "estimated_price": 3250.00,
      "available_vehicles": 3,
      "deal_probability": 95
    }
  ]
}
```

#### Select Price Range
```json
POST /api/quotations/enquiries/1/select-price-range/
{
  "price_range_id": 1
}
```

## 🛣️ Vendor Route Management APIs

### Route Management

```
GET  /api/quotations/routes/             # List vendor's routes
POST /api/quotations/routes/             # Create new route
GET  /api/quotations/routes/{id}/        # Get route details
PUT  /api/quotations/routes/{id}/        # Update route
DELETE /api/quotations/routes/{id}/      # Delete route
```

#### Create Route
```json
POST /api/quotations/routes/
{
  "name": "Mumbai to Delhi Express",
  "description": "Regular route with multiple truck types",
  "truck_type": "Medium",
  "is_regular": true,
  "stops": [
    {
      "sequence": 1,
      "location": "Mumbai, Maharashtra",
      "latitude": 19.0760,
      "longitude": 72.8777,
      "is_pickup": true,
      "is_dropoff": false
    },
    {
      "sequence": 2,
      "location": "Delhi",
      "latitude": 28.7041,
      "longitude": 77.1025,
      "is_pickup": false,
      "is_dropoff": true
    }
  ],
  "pricing": [
    {
      "vehicles_from": 1,
      "vehicles_to": 2,
      "price_per_vehicle": 2500.00
    },
    {
      "vehicles_from": 3,
      "vehicles_to": 5,
      "price_per_vehicle": 2300.00
    }
  ]
}
```

## 🎭 Manager Dashboard APIs

### Manager Operations

```
GET  /api/quotations/manager/enquiries/  # List all enquiries for management
POST /api/quotations/manager/enquiries/{id}/send-to-vendors/  # Send enquiry to vendors
GET  /api/quotations/manager/vendor-requests/  # List all vendor requests
POST /api/quotations/manager/vendor-requests/{id}/confirm/  # Confirm vendor response
```

#### Send Enquiry to Vendors
```json
POST /api/quotations/manager/enquiries/1/send-to-vendors/
{
  "vendor_ids": [1, 2, 3],
  "message": "Customer looking for 2 Medium trucks from Mumbai to Delhi"
}
```

#### Manager Dashboard Response
```json
{
  "pending_enquiries": 5,
  "active_vendor_requests": 12,
  "completed_orders": 45,
  "enquiries": [
    {
      "id": 1,
      "customer_name": "John Doe",
      "pickup_address": "Mumbai, Maharashtra",
      "delivery_address": "Delhi",
      "truck_type": "Medium",
      "number_of_vehicles": 2,
      "status": "vendor_requests_sent",
      "assigned_manager": "manager@example.com",
      "created_at": "2025-07-15T10:00:00Z"
    }
  ]
}
```

## 🚛 Vendor Response APIs

### Vendor Enquiry Management

```
GET  /api/quotations/vendor/requests/    # List vendor's enquiry requests
POST /api/quotations/vendor/requests/{id}/respond/  # Respond to enquiry
GET  /api/quotations/vendor/orders/      # List vendor's confirmed orders
```

#### Vendor Response
```json
POST /api/quotations/vendor/requests/1/respond/
{
  "response_type": "accept",
  "quoted_price": 2400.00,
  "notes": "We can provide 2 Medium trucks with experienced drivers",
  "estimated_delivery_time": "8 hours"
}
```

Response types:
- `accept`: Accept the enquiry at quoted price
- `renegotiate`: Propose different terms
- `reject`: Decline the enquiry

## 🚛 Truck Management APIs

### Public APIs (No Authentication Required)

```
GET  /api/trucks/types/                  # List all truck types
GET  /api/trucks/search/                 # Search trucks by location
GET  /api/trucks/                        # List all active trucks
GET  /api/trucks/{id}/                   # Get truck details
GET  /api/trucks/{truck_id}/images/      # List truck images
```

### Vendor APIs (Authentication Required - Vendor Role)

```
POST /api/trucks/                        # Create new truck
PUT  /api/trucks/{id}/                   # Update truck
DELETE /api/trucks/{id}/                 # Delete truck
GET  /api/trucks/vendor/my-trucks/       # List vendor's trucks

GET  /api/trucks/vendor/drivers/         # List vendor's drivers
POST /api/trucks/vendor/drivers/         # Create new driver
GET  /api/trucks/vendor/drivers/{id}/    # Get driver details
PUT  /api/trucks/vendor/drivers/{id}/    # Update driver
DELETE /api/trucks/vendor/drivers/{id}/  # Delete driver

POST /api/trucks/vendor/upload-image/    # Upload truck image
POST /api/trucks/vendor/{truck_id}/location/              # Update truck location
GET  /api/trucks/vendor/{truck_id}/location-history/      # Get location history
```

## � Complete Tracking Trucks Workflow

### 1. Customer Journey - New Enquiry System

```bash
# 1. Customer submits enquiry (no vendor visibility)
POST /api/quotations/enquiries/
{
  "pickup_latitude": 19.0760,
  "pickup_longitude": 72.8777,
  "pickup_address": "Mumbai, Maharashtra",
  "pickup_date": "2025-07-15T10:00:00Z",
  "delivery_latitude": 28.7041,
  "delivery_longitude": 77.1025,
  "delivery_address": "Delhi",
  "delivery_date": "2025-07-15T18:00:00Z",
  "truck_type": "Medium",
  "load_description": "Electronics goods",
  "estimated_weight": 5.0,
  "number_of_vehicles": 2,
  "special_instructions": "Handle with care"
}

# 2. System returns price ranges (not vendor details)
# Response includes available vehicles and deal probability

# 3. Customer selects preferred price range
POST /api/quotations/enquiries/1/select-price-range/
{
  "price_range_id": 1
}

# 4. System assigns manager and sends to vendors
# Customer waits for manager to coordinate responses

# 5. Customer confirms order after vendor acceptance
POST /api/quotations/enquiries/1/confirm/
{
  "additional_instructions": "Please call before pickup"
}

# 6. Customer tracks order through existing order APIs
GET /api/orders/1/tracking/
```

### 2. Manager Journey - Mediation Workflow

```bash
# 1. Manager views all pending enquiries
GET /api/quotations/manager/enquiries/

# 2. Manager sends enquiry to appropriate vendors
POST /api/quotations/manager/enquiries/1/send-to-vendors/
{
  "vendor_ids": [1, 2, 3],
  "message": "Customer needs 2 Medium trucks from Mumbai to Delhi"
}

# 3. Manager reviews vendor responses
GET /api/quotations/manager/vendor-requests/

# 4. Manager confirms best vendor response
POST /api/quotations/manager/vendor-requests/5/confirm/
{
  "confirmation_notes": "Best price and availability confirmed"
}

# 5. Manager coordinates final order creation
# System creates order when both parties confirm
```

### 3. Vendor Journey - Route-Based Responses

```bash
# 1. Vendor defines regular routes
POST /api/quotations/routes/
{
  "name": "Mumbai to Delhi Express",
  "description": "Regular route with competitive pricing",
  "truck_type": "Medium",
  "is_regular": true,
  "stops": [
    {
      "sequence": 1,
      "location": "Mumbai, Maharashtra",
      "latitude": 19.0760,
      "longitude": 72.8777,
      "is_pickup": true,
      "is_dropoff": false
    },
    {
      "sequence": 2,
      "location": "Delhi",
      "latitude": 28.7041,
      "longitude": 77.1025,
      "is_pickup": false,
      "is_dropoff": true
    }
  ],
  "pricing": [
    {
      "vehicles_from": 1,
      "vehicles_to": 2,
      "price_per_vehicle": 2500.00
    },
    {
      "vehicles_from": 3,
      "vehicles_to": 5,
      "price_per_vehicle": 2300.00
    }
  ]
}

# 2. Vendor responds to enquiry requests
POST /api/quotations/vendor/requests/1/respond/
{
  "response_type": "accept",
  "quoted_price": 2400.00,
  "notes": "Regular route with experienced drivers",
  "estimated_delivery_time": "8 hours"
}

# 3. Vendor manages confirmed orders
GET /api/quotations/vendor/orders/
```

### 4. Business Rules Enforced

#### No Direct Vendor Exposure
- Customers never see vendor details until order confirmation
- Price ranges generated from multiple vendor routes
- Manager mediates all vendor communication

#### Route-Based Pricing
- Vendors define regular routes with fixed pricing
- Miscellaneous routes get estimated pricing with markup
- Automatic route matching for accurate quotes

#### Manager Mediation
- All vendor-customer communication through managers
- Managers assigned based on workload
- Both parties must confirm before order creation

## 📦 Order Management APIs

### Customer APIs

```
POST /api/orders/create/                 # Create order from confirmed enquiry
GET  /api/orders/customer/orders/        # List customer's orders
POST /api/orders/{order_id}/verify-delivery/  # Verify delivery with OTP
```

### Vendor APIs

```
GET  /api/orders/vendor/orders/          # List vendor's orders
POST /api/orders/{order_id}/update-status/      # Update order status
POST /api/orders/{order_id}/assign-driver/      # Assign driver to order
POST /api/orders/{order_id}/update-location/    # Update order location (tracking)
```

### Manager APIs

```
GET  /api/orders/manager/orders/         # List all orders for monitoring
POST /api/orders/{order_id}/intervene/   # Manager intervention if needed
```

### Common APIs

```
GET  /api/orders/{id}/                   # Get order details
GET  /api/orders/{order_id}/tracking/    # Get order tracking history
GET  /api/orders/{order_id}/status-history/     # Get order status history
GET  /api/orders/{order_id}/documents/   # List order documents
POST /api/orders/documents/upload/       # Upload order document
```

## 💳 Payment Management APIs

### Customer APIs

```
POST /api/payments/create/               # Create payment
POST /api/payments/initiate/             # Initiate payment with gateway
GET  /api/payments/                      # List user's payments
```

### Common APIs

```
GET  /api/payments/{id}/                 # Get payment details
GET  /api/payments/order/{order_id}/     # List payments for order
GET  /api/payments/{payment_id}/history/ # Get payment history
POST /api/payments/complete/             # Complete payment (webhook)
```

### Invoice APIs

```
POST /api/payments/invoices/create/      # Create invoice (vendor)
GET  /api/payments/invoices/             # List invoices
GET  /api/payments/invoices/{id}/        # Get invoice details
GET  /api/payments/invoices/{invoice_id}/download/  # Download invoice PDF
POST /api/payments/invoices/{invoice_id}/generate/  # Generate invoice PDF
GET  /api/payments/vendor/stats/         # Get payment statistics (vendor)
```

## � Sample Data

The application includes sample data with:
- **3 Vendors** with predefined routes
- **6 Trucks** of various types and capacities
- **6 Drivers** assigned to different vendors
- **3 Customers** for testing
- **2 Managers** for enquiry mediation
- **6 Truck Types** (Mini, Small, Medium, Large, Container, Refrigerated)

### Sample Login Credentials

**Admin:**
- Email: `admin@truckrent.com`
- Password: `admin123`

**Managers:**
- Email: `manager1@truckrent.com`, Password: `manager123`
- Email: `manager2@truckrent.com`, Password: `manager123`

**Vendors:**
- Email: `vendor1@truckrent.com`, Password: `vendor123`
- Email: `vendor2@truckrent.com`, Password: `vendor123`
- Email: `vendor3@truckrent.com`, Password: `vendor123`

**Customers:**
- Email: `customer1@example.com`, Password: `customer123`
- Email: `customer2@example.com`, Password: `customer123`
- Email: `customer3@example.com`, Password: `customer123`

## 🚀 Features Implemented

### ✅ Phase 1: Route-Based Pricing System
- ✅ Vendor route definition with stops and pricing
- ✅ Automatic route matching for enquiries
- ✅ Miscellaneous route handling with estimated pricing
- ✅ Price range generation without vendor exposure

### ✅ Phase 2: Manager-Mediated Workflow
- ✅ **Manager Role**: New user role for enquiry mediation
- ✅ **Enquiry Assignment**: Automatic manager assignment based on workload
- ✅ **Vendor Communication**: Managers send enquiries to relevant vendors
- ✅ **Response Coordination**: Managers review and confirm vendor responses

### ✅ Phase 3: Customer Enquiry System
- ✅ **No Vendor Visibility**: Customers see price ranges, not vendor details
- ✅ **Deal Probability**: Show chances of getting selected price range
- ✅ **Multiple Vehicle Support**: Handle enquiries for multiple vehicles
- ✅ **Route Type Classification**: Direct, via-stops, or miscellaneous routes

### ✅ Phase 4: Vendor Response System
- ✅ **Route-Based Pricing**: Vendors define regular routes with fixed prices
- ✅ **Enquiry Response**: Accept, renegotiate, or reject manager requests
- ✅ **Pricing Flexibility**: Different prices for bulk orders
- ✅ **Confirmation Required**: Both parties must confirm before order

### ✅ Phase 5: Enhanced Business Logic
- ✅ **Manager Mediation**: All communication through managers
- ✅ **Route Matching**: Intelligent matching of enquiries to vendor routes
- ✅ **Price Range Generation**: Dynamic pricing from multiple vendors
- ✅ **Dual Confirmation**: Both customer and vendor must confirm

### ✅ Additional Features
- ✅ Document upload system
- ✅ Rate limiting for security
- ✅ Comprehensive admin interface
- ✅ Role-based permissions
- ✅ Distance calculation for pricing
- ✅ Truck availability management
- ✅ **Manager dashboard** for enquiry management
- ✅ **Route-based vendor pricing**

## 🛠️ Technology Stack

- **Backend**: Django 4.2.4 + Django REST Framework 3.14.0
- **Authentication**: JWT with djangorestframework-simplejwt
- **Database**: SQLite (development) / PostgreSQL (production ready)
- **File Storage**: Local storage with Pillow for images
- **Additional**: Redis for caching, CORS support, Rate limiting

## 🔧 Installation & Setup

```bash
# 1. Clone and navigate to project
cd /path/to/DRF-Boilerplate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
python manage.py migrate

# 4. Create sample data
python manage.py create_sample_data

# 5. Start development server
python manage.py runserver
```

## 📝 API Response Formats

### Success Response
```json
{
  "id": 1,
  "field1": "value1",
  "field2": "value2"
}
```

### Error Response
```json
{
  "error": "Error message description"
}
```

### Validation Error Response
```json
{
  "field_name": ["This field is required."],
  "another_field": ["Invalid choice."]
}
```

This completes the full implementation of the "Uber for Transport" truck rental platform with all features from the README successfully implemented and ready for use! 🎉
