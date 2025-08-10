# Frontend Integration Guide - Quotation & Negotiation System

## 🎯 Overview
This guide provides complete API documentation for frontend integration of the quotation and negotiation system with expected request/response objects.

## 🔄 Negotiation Flow Logic
**Customer-Initiated Quotation System:**

1. **Customer creates quotation request** → 
   - Customer specifies their budget/expected price
   - `customer_initial_proposal` negotiation record created
   - Quotation status = `'negotiating'`

2. **Vendors respond to customer request** →
   - Vendors submit their quotes via separate endpoint
   - Vendor quotation status = `'sent'`

3. **Negotiation begins** →
   - Each party can counter-offer via `/negotiations/create/`
   - Complete audit trail maintained

**Benefits:**
- ✅ Customer-driven pricing (more realistic business model)
- ✅ Vendors respond to actual customer demand
- ✅ Complete transparency in price expectations
- ✅ Clear separation between customer requests and vendor responses

## 🛠️ Base Configuration
```javascript
const API_BASE_URL = "http://localhost:8000/api/quotations/";
const headers = {
  "Authorization": "Bearer <JWT_TOKEN>",
  "Content-Type": "application/json"
};
```

---

## 👤 CUSTOMER JOURNEY

### 1. Create Quotation Request (Customer Sets Budget)
**Endpoint:** `POST /quotations/requests/create/`

**Request:**
```json
{
  "vendorId": 1,
  "vendorName": "ABC Transport",
  "totalAmount": 45000.00,  // Customer's budget/expected price
  "customer_proposed_amount": 400000.00
  "customerNegotiationMessage": "Looking for transport service within this budget",
  "items": [
    {
      "vehicle_type": "Mini Truck",
      "quantity": 1,
      "unit_price": 45000.00,
      "description": "Mini truck for local delivery"
    }
  ],
  "searchParams": {
    "originPinCode": "400001",
    "destinationPinCode": "110001",
    "pickupDate": "2025-08-15T10:00:00Z",
    "dropDate": "2025-08-16T18:00:00Z",
    "weight": 2.5,
    "weightUnit": "ton",
    "vehicleType": "Mini Truck",
    "urgencyLevel": "medium"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "quotation_request": {
      "id": 123,
      "origin_pincode": "400001",
      "destination_pincode": "110001",
      "pickup_date": "2025-08-15",
      "drop_date": "2025-08-16",
      "weight": "2.5",
      "weight_unit": "ton",
      "vehicle_type": "Mini Truck",
      "urgency_level": "medium",
      "total_quotations": 1,
      "created_at": "2025-08-10T12:00:00Z"
    },
    "quotation": {
      "id": 456,
      "vendor_id": 1,
      "vendor_name": "ABC Transport",
      "items": [...],
      "total_amount": "45000.00",
      "status": "negotiating",
      "validity_hours": 24,
      "created_at": "2025-08-10T12:00:00Z",
      "updated_at": "2025-08-10T12:00:00Z"
    },
    "customer_negotiation": {
      "id": 789,
      "initiated_by": "customer",
      "proposed_amount": "45000.00",
      "message": "Looking for transport service within this budget",
      "created_at": "2025-08-10T12:00:00Z"
    },
    "created_new_request": true,
    "message": "Quotation request created for route 400001 to 110001 with your budget proposal"
  },
  "message": "Quotation request created for route 400001 to 110001 with your budget proposal"
}
```

### 2. View Negotiation History
**Endpoint:** `GET /quotations/{quotation_id}/negotiations/`

**Response:**
```json
{
  "success": true,
  "data": {
    "quotation": {
      "id": 456,
      "original_amount": "50000.00",
      "current_negotiated_amount": "47000.00",
      "status": "negotiating",
      "vendor_name": "ABC Transport",
      "can_negotiate": true
    },
    "negotiations": [
      {
        "id": 788,
        "quotation": 456,
        "initiated_by": "vendor",
        "proposed_amount": "50000.00",
        "message": "Initial quotation offer from ABC Transport",
        "created_at": "2025-08-10T12:00:00Z"
      },
      {
        "id": 789,
        "quotation": 456,
        "initiated_by": "customer",
        "proposed_amount": "45000.00",
        "message": "Can we do it for 45k?",
        "created_at": "2025-08-10T12:00:00Z"
      },
      {
        "id": 790,
        "quotation": 456,
        "initiated_by": "vendor",
        "proposed_amount": "47000.00",
        "message": "Best I can do is 47k",
        "created_at": "2025-08-10T12:30:00Z"
      }
    ],
    "total_negotiations": 3,
    "latest_negotiation": {
      "initiated_by": "vendor",
      "proposed_amount": "47000.00",
      "message": "Best I can do is 47k",
      "created_at": "2025-08-10T12:30:00Z"
    },
    "next_negotiator": "customer"
  },
  "message": "Found 2 negotiations for quotation"
}
```

### 3. Create Counter-Offer
**Endpoint:** `POST /quotations/{quotation_id}/negotiations/create/`

**Request:**
```json
{
  "proposed_amount": 46000.00,
  "message": "How about 46k?",
  "proposed_base_price": 40000.00,     // Optional breakdown
  "proposed_fuel_charges": 6000.00,    // Optional breakdown
  "proposed_toll_charges": 0.00,       // Optional breakdown
  "proposed_loading_charges": 0.00,    // Optional breakdown
  "proposed_unloading_charges": 0.00,  // Optional breakdown
  "proposed_additional_charges": 0.00  // Optional breakdown
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "negotiation": {
      "id": 791,
      "quotation_id": 456,
      "initiated_by": "customer",
      "proposed_amount": "46000.00",
      "message": "How about 46k?",
      "proposed_base_price": "40000.00",
      "proposed_fuel_charges": "6000.00",
      "proposed_toll_charges": null,
      "proposed_loading_charges": null,
      "proposed_unloading_charges": null,
      "proposed_additional_charges": null,
      "created_at": "2025-08-10T13:00:00Z"
    },
    "quotation_status": "negotiating"
  },
  "message": "Negotiation offer created successfully by customer"
}
```

### 4. Accept Vendor's Negotiation
**Endpoint:** `POST /quotations/negotiations/{negotiation_id}/accept/`

**Request:** `{}` (Empty body)

**Response:**
```json
{
  "success": true,
  "data": {
    "negotiation_accepted": {
      "id": 790,
      "initiated_by": "vendor",
      "accepted_by": "customer",
      "original_amount": "50000.00",
      "final_amount": "47000.00",
      "savings": "3000.00",
      "message": "Best I can do is 47k"
    },
    "quotation": {
      "id": 456,
      "vendor_name": "ABC Transport",
      "status": "accepted",
      "total_negotiations": 2
    },
    "quotation_request_id": 123,
    "other_quotations_rejected": 0
  },
  "message": "Negotiation accepted! Final amount: ₹47000.00 (Saved ₹3000.00)"
}
```

### 5. Accept Quotation Directly (Without Negotiation)
**Endpoint:** `POST /quotations/{quotation_id}/accept/`

**Request:** `{}` (Empty body)

**Response:**
```json
{
  "success": true,
  "data": {
    "quotation": {
      "id": 456,
      "vendor_name": "ABC Transport",
      "original_amount": "50000.00",
      "final_amount": "47000.00",  // Latest negotiated amount if any
      "status": "accepted",
      "negotiations_count": 2
    },
    "quotation_request_id": 123,
    "other_quotations_rejected": 1,
    "has_negotiations": true
  },
  "message": "Quotation accepted successfully. Final amount: ₹47000.00"
}
```

### 6. Reject Quotation
**Endpoint:** `POST /quotations/{quotation_id}/reject/`

**Request:** `{}` (Empty body)

**Response:**
```json
{
  "success": true,
  "data": {
    "quotation": {
      "id": 456,
      "vendor_name": "ABC Transport",
      "original_amount": "50000.00",
      "status": "rejected",
      "negotiations_count": 2
    },
    "quotation_request_id": 123,
    "had_negotiations": true,
    "latest_negotiated_amount": "47000.00"
  },
  "message": "Quotation rejected successfully"
}
```

---

## 🚛 VENDOR JOURNEY

### 1. Respond to Customer Request
**Endpoint:** `POST /quotations/vendor/respond/`

**Request:**
```json
{
  "vendor_name": "ABC Transport",
  "total_amount": 48000.00,
  "origin_pincode": "400001",
  "destination_pincode": "110001", 
  "pickup_date": "2025-08-15T10:00:00Z",
  "drop_date": "2025-08-16T18:00:00Z",
  "weight": "2.5",
  "weight_unit": "ton",
  "urgency_level": "medium",
  "items": [
    {
      "vehicle_id": 101,
      "vehicle_model": "Tata Ace",
      "vehicle_type": "Mini Truck",
      "max_weight": "2 tons",
      "gps_number": "GPS001",
      "unit_price": "48000.00"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "quotation_request": {
      "id": 123,
      "customer_name": "John Doe",
      "origin_pincode": "400001",
      "destination_pincode": "110001",
      "pickup_date": "2025-08-15",
      "drop_date": "2025-08-16",
      "weight": "2.5",
      "weight_unit": "ton",
      "vehicle_type": "Mini Truck",
      "urgency_level": "medium",
      "total_quotations": 2,
      "created_at": "2025-08-10T12:00:00Z"
    },
    "quotation": {
      "id": 457,
      "vendor_name": "ABC Transport",
      "items": [...],
      "total_amount": "48000.00",
      "status": "sent",
      "validity_hours": 24,
      "created_at": "2025-08-10T14:00:00Z",
      "updated_at": "2025-08-10T14:00:00Z"
    },
    "quotation_updated": false,
    "message": "Quotation submitted for customer request 400001 to 110001"
  },
  "message": "Quotation submitted for customer request 400001 to 110001"
}
```

### 2. View Customer's Quotation Request with Negotiations
**Endpoint:** `GET /quotations/{quotation_id}/negotiations/`

**Response:** (Same as customer's view above)

### 2. Create Counter-Offer to Customer
**Endpoint:** `POST /quotations/{quotation_id}/negotiations/create/`

**Request:**
```json
{
  "proposed_amount": 48000.00,
  "message": "Best I can do is 48k due to fuel costs",
  "proposed_base_price": 42000.00,
  "proposed_fuel_charges": 6000.00
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "negotiation": {
      "id": 792,
      "quotation_id": 456,
      "initiated_by": "vendor",
      "proposed_amount": "48000.00",
      "message": "Best I can do is 48k due to fuel costs",
      "proposed_base_price": "42000.00",
      "proposed_fuel_charges": "6000.00",
      "created_at": "2025-08-10T14:00:00Z"
    },
    "quotation_status": "negotiating"
  },
  "message": "Negotiation offer created successfully by vendor"
}
```

### 3. Accept Customer's Negotiation
**Endpoint:** `POST /quotations/negotiations/{negotiation_id}/accept/`

**Request:** `{}` (Empty body)

**Response:**
```json
{
  "success": true,
  "data": {
    "negotiation_accepted": {
      "id": 791,
      "initiated_by": "customer",
      "accepted_by": "vendor",
      "original_amount": "50000.00",
      "final_amount": "46000.00",
      "savings": "4000.00",  // From customer's perspective
      "message": "How about 46k?"
    },
    "quotation": {
      "id": 456,
      "vendor_name": "ABC Transport",
      "status": "accepted",
      "total_negotiations": 3
    },
    "quotation_request_id": 123,
    "other_quotations_rejected": 0
  },
  "message": "Negotiation accepted! Final amount: ₹46000.00 (Saved ₹4000.00)"
}
```

---

## 🚨 ERROR RESPONSES

### Common Error Format:
```json
{
  "success": false,
  "data": null,
  "message": "",
  "error": "Detailed error message",
  "errors": {
    "field_name": ["Field-specific error messages"]
  }
}
```

### Common Error Scenarios:

#### 1. Validation Errors (400)
```json
{
  "success": false,
  "error": "Validation failed",
  "errors": {
    "proposed_amount": ["Proposed amount must be positive"],
    "breakdown_sum": ["Breakdown sum does not match proposed amount"]
  }
}
```

#### 2. Permission Denied (403)
```json
{
  "success": false,
  "error": "You can only negotiate quotations for your own requests"
}
```

#### 3. Business Logic Errors (400)
```json
{
  "success": false,
  "error": "Cannot negotiate quotation with status 'accepted'"
}
```

#### 4. Self-Acceptance Error (400)
```json
{
  "success": false,
  "error": "You cannot accept your own negotiation offer"
}
```

#### 5. Not Found (404)
```json
{
  "success": false,
  "error": "Quotation not found"
}
```

---

## 📱 Frontend Implementation Tips

### 1. State Management
```javascript
// React/Redux example
const quotationState = {
  quotationRequest: null,
  currentQuotation: null,
  negotiations: [],
  canNegotiate: false,
  nextNegotiator: null,
  isLoading: false
};
```

### 2. Conditional UI Rendering
```javascript
// Show negotiation button only if allowed
const canCreateNegotiation = 
  quotation.status === 'negotiating' && 
  nextNegotiator === currentUserRole;

// Show accept button only for other party's offers
const canAcceptNegotiation = 
  latestNegotiation.initiated_by !== currentUserRole;
```

### 3. Real-time Updates
Consider implementing WebSocket connections for real-time negotiation updates:
```javascript
// WebSocket endpoint (if implemented)
const ws = new WebSocket(`ws://localhost:8000/ws/quotations/${quotationId}/`);
```

### 4. Amount Formatting
```javascript
const formatAmount = (amount) => `₹${parseFloat(amount).toLocaleString('en-IN')}`;
```

---

## 🔄 Complete Flow Summary

1. **Customer creates request with budget** → Creates quotation request + customer's initial price expectation
2. **Vendors respond with quotes** → Each vendor submits their pricing via `/vendor/respond/`
3. **Negotiations begin** → Customer/vendor can negotiate via `/negotiations/create/`
4. **Final acceptance** → Quotation status becomes 'accepted' with final negotiated amount
5. **Other quotations auto-rejected** → Clean state management

**Key Improvement:** Now follows realistic business model where customers drive the demand and set price expectations, then vendors compete with their best offers!

This system ensures a smooth, real-time negotiation experience with comprehensive error handling and state management! 🚀
