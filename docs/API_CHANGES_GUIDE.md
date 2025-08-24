# API Changes - Order Management System

## 🔄 **Updated API Endpoints**

### **1. Order Creation - `POST /api/orders/`**

**Before:**
```python
# Manual order creation with manual status history
order = Order.objects.create(...)
OrderStatusHistory.objects.create(...)  # Manual creation
```

**After:**
```python
# Automatic order creation using OrderCreationService
order_result = OrderCreationService.create_order_from_quotation(...)
# OrderStatusHistory automatically created
```

**Response Changes:**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "order_number": "ORD-2024-001234",
    "status": "created",
    "delivery_otp": "123456",
    "customer_name": "John Doe",
    "vendor_name": "ABC Logistics",
    // ... other order fields
  },
  "message": "Order created successfully"
}
```

---

### **2. Status Update - `POST /api/orders/{id}/status/`**

**Before:**
```python
# Manual status update with scattered logic
order.status = new_status
order.save()
OrderStatusHistory.objects.create(...)  # Manual
if new_status == 'completed':
    order.truck.availability_status = 'available'  # Manual
    order.truck.save()
```

**After:**
```python
# Centralized status tracking with automatic business logic
OrderStatusTrackingService.update_order_status(
    order=order,
    new_status=new_status,
    updated_by=user,
    notes=notes,
    **context
)
# Everything handled automatically
```

**Request:**
```json
{
  "status": "driver_assigned",
  "notes": "Driver John assigned to this order",
  "driver_id": 456,
  "latitude": 28.6139,
  "longitude": 77.2090
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "order_id": 123,
    "previous_status": "confirmed",
    "new_status": "driver_assigned",
    "status_history_id": 789,
    "context": {
      "driver_assigned": "John Doe"
    }
  },
  "message": "Order status updated to driver_assigned"
}
```

---

### **3. Accept Negotiation - `POST /api/quotations/negotiations/{id}/accept/`**

**Before:**
```python
# THIS METHOD DIDN'T EXIST - would cause 500 error
QuotationStatusService.accept_negotiation(...)  # ❌ AttributeError
```

**After:**
```python
# Now properly implemented with order creation
result = QuotationStatusService.accept_negotiation(
    negotiation=negotiation,
    user=user
)
# Creates order automatically with negotiated amount
```

**Response:**
```json
{
  "success": true,
  "data": {
    "negotiation": {
      "id": 123,
      "status": "accepted",
      "proposed_amount": "15000.00"
    },
    "order": {
      "id": 456,
      "order_number": "ORD-2024-001234",
      "status": "created",
      "total_amount": "15000.00"
    },
    "order_metadata": {
      "negotiation_id": 123,
      "original_amount": "18000.00",
      "final_amount": "15000.00",
      "savings": "3000.00",
      "delivery_otp": "654321"
    }
  },
  "message": "Negotiation accepted and order created successfully"
}
```

---

## 🛡️ **Error Handling Improvements**

### **Status Transition Validation**

**Before:**
```python
# No validation - could set any status
order.status = 'delivered'  # Even from 'created' - invalid!
```

**After:**
```python
# Automatic validation with clear error messages
try:
    OrderStatusTrackingService.update_order_status(...)
except ValidationError as e:
    # Returns: "Invalid status transition from 'created' to 'delivered'. Valid transitions: ['confirmed', 'cancelled']"
```

**Error Response:**
```json
{
  "success": false,
  "error": "Invalid status transition from 'created' to 'delivered'. Valid transitions: ['confirmed', 'cancelled']",
  "error_code": "INVALID_STATUS_TRANSITION"
}
```

### **Role-Based Permission Validation**

**Error Response:**
```json
{
  "success": false,
  "error": "User role 'customer' cannot set status to 'driver_assigned'",
  "error_code": "INSUFFICIENT_PERMISSIONS"
}
```

---

## 📱 **Frontend Integration Guide**

### **Handle New Response Formats**

```javascript
// Order creation
const createOrder = async (quotationId, instructions) => {
  const response = await fetch('/api/orders/', {
    method: 'POST',
    body: JSON.stringify({
      quotation_id: quotationId,
      special_instructions: instructions.special,
      delivery_instructions: instructions.delivery
    })
  });
  
  const result = await response.json();
  
  if (result.success) {
    const order = result.data;
    // Store delivery OTP for later use
    localStorage.setItem(`order_${order.id}_otp`, order.delivery_otp);
    
    // Show success message
    showNotification(`Order #${order.order_number} created successfully!`);
  }
};

// Status updates with context
const updateOrderStatus = async (orderId, statusData) => {
  const response = await fetch(`/api/orders/${orderId}/status/`, {
    method: 'POST',
    body: JSON.stringify(statusData)
  });
  
  const result = await response.json();
  
  if (result.success) {
    const { previous_status, new_status, context } = result.data;
    
    // Update UI with transition info
    updateOrderTimeline(orderId, previous_status, new_status);
    
    // Handle specific contexts
    if (context.driver_assigned) {
      showNotification(`Driver ${context.driver_assigned} assigned to order`);
    }
    
    if (context.truck_freed) {
      showNotification('Truck is now available for new orders');
    }
  }
};

// Accept negotiation with savings info
const acceptNegotiation = async (negotiationId) => {
  const response = await fetch(`/api/quotations/negotiations/${negotiationId}/accept/`, {
    method: 'POST'
  });
  
  const result = await response.json();
  
  if (result.success) {
    const { order, order_metadata } = result.data;
    const savings = order_metadata.savings;
    
    showNotification(
      `Negotiation accepted! Order created with ₹${savings} savings.`
    );
    
    // Redirect to order details
    window.location.href = `/orders/${order.id}`;
  }
};
```

---

## 🔍 **Debugging & Monitoring**

### **Order Analytics API**

```python
# Get comprehensive order analytics
analytics = OrderAnalyticsService.get_order_analytics(order)

# Use in API endpoint
@api_view(['GET'])
def order_analytics(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    analytics = OrderAnalyticsService.get_order_analytics(order)
    return Response(analytics)
```

### **Status Timeline Tracking**

```json
{
  "order_id": 123,
  "current_status": "delivered",
  "total_status_changes": 7,
  "status_timeline": [
    {
      "status": "created",
      "timestamp": "2024-01-15T09:00:00Z",
      "updated_by": "John Doe",
      "notes": "Order created from accepted quotation"
    },
    {
      "status": "confirmed",
      "timestamp": "2024-01-15T09:30:00Z",
      "updated_by": "ABC Logistics",
      "notes": "Order confirmed by vendor"
    }
  ],
  "estimated_vs_actual": {
    "pickup_scheduled": "2024-01-15T10:00:00Z",
    "pickup_actual": "2024-01-15T10:15:00Z",
    "delivery_scheduled": "2024-01-15T18:00:00Z",
    "delivery_actual": "2024-01-15T17:45:00Z"
  }
}
```

---

## 🧪 **Testing the Changes**

### **Quick API Test**

```bash
# Test order creation
curl -X POST http://localhost:8000/api/orders/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "quotation_id": 1,
    "special_instructions": "Test order creation",
    "delivery_instructions": "Call before delivery"
  }'

# Test status update  
curl -X POST http://localhost:8000/api/orders/1/status/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "confirmed",
    "notes": "Order confirmed via API test"
  }'

# Test negotiation acceptance
curl -X POST http://localhost:8000/api/quotations/negotiations/1/accept/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

The new system provides a much more robust, automatic, and maintainable approach to order management! 🚀
