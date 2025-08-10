# QuotationCreateView API Documentation

## Overview
The `QuotationCreateView` allows customers to create quotation requests by selecting specific vendors and their vehicles. This matches the TypeScript interface where customers can browse available vehicles from vendors and submit requests.

## Request Format

### Expected TypeScript Interface
```typescript
export interface QuotationRequest {
  vendorId: number;
  vendorName: string;
  items: QuotationItem[];
  totalAmount: number;
  searchParams: {
    originPinCode: string;
    destinationPinCode: string;
    pickupDate: string;
    dropDate: string;
    weight: string;
    weightUnit: string;
    vehicleType?: string;
    urgencyLevel: string;
  };
}

export interface QuotationItem {
  vehicle: {
    id: string;
    model: string;
    vehicleType: string;
    maxWeight: string;
    gpsNumber: string;
    total: string;
    estimatedDelivery: string;
  };
  quantity: number;
}
```

### Actual Request Body Example
```json
{
  "vendorId": 5,
  "vendorName": "Mumbai Transport Services",
  "totalAmount": 12500.00,
  "items": [
    {
      "vehicle": {
        "id": "TRK001",
        "model": "Tata LPT 1618",
        "vehicleType": "Large Truck",
        "maxWeight": "10.5 tons",
        "gpsNumber": "GPS001",
        "total": "8500.00",
        "estimatedDelivery": "2024-01-25T18:00:00Z"
      },
      "quantity": 1
    },
    {
      "vehicle": {
        "id": "TRK002", 
        "model": "Mahindra Bolero Pickup",
        "vehicleType": "Mini Truck",
        "maxWeight": "1.5 tons",
        "gpsNumber": "GPS002",
        "total": "4000.00",
        "estimatedDelivery": "2024-01-25T16:00:00Z"
      },
      "quantity": 1
    }
  ],
  "searchParams": {
    "originPinCode": "400001",
    "destinationPinCode": "560001",
    "pickupDate": "2024-01-25T08:00:00Z",
    "dropDate": "2024-01-25T18:00:00Z",
    "weight": "12.0",
    "weightUnit": "ton",
    "vehicleType": "Mixed",
    "urgencyLevel": "medium"
  },
  "customerProposedAmount": 11000.00,
  "customerNegotiationMessage": "Can we negotiate the price? My budget is ₹11,000"
}
```

## API Endpoint

**POST** `/api/quotations/create/`

### Headers
```
Authorization: Bearer <customer_jwt_token>
Content-Type: application/json
```

### Response Format

#### Success Response (201 Created)
```json
{
  "success": true,
  "data": {
    "quotation_request": {
      "id": 123,
      "origin_pincode": "400001",
      "destination_pincode": "560001",
      "pickup_date": "2024-01-25T08:00:00Z",
      "drop_date": "2024-01-25T18:00:00Z",
      "weight": "12.0",
      "weight_unit": "ton",
      "vehicle_type": "Mixed",
      "urgency_level": "medium",
      "total_quotations": 1,
      "created_at": "2024-01-20T10:30:00Z"
    },
    "quotation": {
      "id": 456,
      "vendor_id": 5,
      "vendor_name": "Mumbai Transport Services",
      "items": [
        {
          "vehicle": {
            "id": "TRK001",
            "model": "Tata LPT 1618",
            "vehicleType": "Large Truck",
            "maxWeight": "10.5 tons",
            "gpsNumber": "GPS001",
            "total": "8500.00",
            "estimatedDelivery": "2024-01-25T18:00:00Z"
          },
          "quantity": 1
        },
        {
          "vehicle": {
            "id": "TRK002",
            "model": "Mahindra Bolero Pickup", 
            "vehicleType": "Mini Truck",
            "maxWeight": "1.5 tons",
            "gpsNumber": "GPS002",
            "total": "4000.00",
            "estimatedDelivery": "2024-01-25T16:00:00Z"
          },
          "quantity": 1
        }
      ],
      "total_amount": "12500.00",
      "status": "negotiating",
      "validity_hours": 24,
      "created_at": "2024-01-20T10:30:00Z",
      "updated_at": "2024-01-20T10:30:00Z"
    },
    "search_params": {
      "origin_pincode": "400001",
      "destination_pincode": "560001",
      "pickup_date": "2024-01-25T08:00:00Z",
      "drop_date": "2024-01-25T18:00:00Z",
      "weight": "12.0",
      "weight_unit": "ton",
      "vehicle_type": "Mixed",
      "urgency_level": "medium"
    },
    "created_new_request": true,
    "customer_negotiation": {
      "id": 789,
      "initiated_by": "customer",
      "proposed_amount": "11000.00",
      "message": "Can we negotiate the price? My budget is ₹11,000",
      "created_at": "2024-01-20T10:30:00Z"
    },
    "message": "Quotation request created for vendor Mumbai Transport Services with selected vehicles"
  },
  "message": "Quotation request created for vendor Mumbai Transport Services with selected vehicles"
}
```

#### Error Response (400 Bad Request)
```json
{
  "success": false,
  "error": "Validation failed",
  "errors": {
    "vendorId": ["Vendor not found or invalid role"],
    "items": ["At least one vehicle item is required"],
    "searchParams": {
      "pickupDate": ["Drop date must be after pickup date"]
    }
  }
}
```

## Business Flow

1. **Customer browses vendors and vehicles** - Frontend shows available vendors and their vehicles for the route
2. **Customer selects vehicles** - Customer picks specific vehicles from vendor inventory
3. **Customer submits request** - POST to this endpoint with vendor and vehicle selection
4. **System creates quotation** - Creates QuotationRequest and Quotation with selected vehicles
5. **Optional negotiation** - If customer provides `customerProposedAmount`, creates initial negotiation
6. **Vendor notification** - Vendor gets notified of customer's request and can accept/negotiate

## Optional Fields

- `customerProposedAmount`: If customer wants to negotiate price immediately
- `customerNegotiationMessage`: Message for vendor explaining price proposal
- `vehicleType` in searchParams: Can be omitted if mixed vehicle types

## Validation Rules

1. `vendorId` must exist and have role 'vendor'
2. `items` array cannot be empty
3. `dropDate` must be after `pickupDate`
4. All vehicle IDs in items should exist in the vendor's truck inventory
5. `totalAmount` should match sum of vehicle totals (frontend calculation)

## Status Flow

1. **pending** - Initial quotation created, waiting for vendor response
2. **negotiating** - Customer provided different amount, negotiation started
3. **sent** - Vendor has responded/confirmed 
4. **accepted** - Customer accepted the quotation
5. **rejected** - Customer rejected the quotation
6. **expired** - Quotation validity period expired

This endpoint enables a marketplace model where customers can browse vendor vehicles, select what they need, and create targeted requests rather than generic route-based enquiries.
