# Order Management System - Architecture & Usage Guide

## 🎯 **Problem Solved**

The new Order Management System addresses the following issues in your truck rental platform:

### **Before (Problems):**
- ❌ Manual OrderStatusHistory creation scattered across codebase
- ❌ Missing QuotationStatusService.accept_negotiation method
- ❌ Inconsistent order creation workflow
- ❌ No automatic status tracking
- ❌ Business logic mixed in serializers
- ❌ No centralized order lifecycle management

### **After (Solutions):**
- ✅ **Centralized OrderCreationService** - Automatic order creation with status history
- ✅ **OrderStatusTrackingService** - Intelligent status transitions with validation
- ✅ **Role-based permissions** - Automatic validation of who can change what
- ✅ **Automatic truck management** - Truck availability updated automatically
- ✅ **Complete QuotationStatusService** - Fixed missing accept_negotiation method
- ✅ **OrderAnalyticsService** - Comprehensive order analytics and reporting

---

## 🏗️ **Architecture Overview**

```
orders/services.py
├── OrderCreationService          # Creates orders from quotations/negotiations
├── OrderStatusTrackingService    # Manages status transitions & history
├── OrderDocumentService          # Handles document uploads with tracking
└── OrderAnalyticsService         # Provides comprehensive analytics

quotations/services.py
└── QuotationStatusService.accept_negotiation()  # Fixed missing method
```

---

## 🚀 **Usage Examples**

### **1. Create Order from Accepted Quotation**

```python
from orders.services import OrderCreationService

# Automatic order creation with status history
order_result = OrderCreationService.create_order_from_quotation(
    quotation=quotation,
    user=customer,
    special_instructions="Handle with care",
    delivery_instructions="Call upon arrival"
)

order = order_result['order']
delivery_otp = order_result['delivery_otp']
# OrderStatusHistory automatically created with status 'created'
```

### **2. Accept Negotiation and Create Order**

```python
from quotations.services import QuotationStatusService

# This method now exists and works properly!
result = QuotationStatusService.accept_negotiation(
    negotiation=negotiation,
    user=customer
)

order = result['order']
savings = result['order_metadata']['savings']
# Order created with negotiated amount
# OrderStatusHistory automatically created
```

### **3. Update Order Status with Automatic Tracking**

```python
from orders.services import OrderStatusTrackingService

# Intelligent status updates with validation
status_result = OrderStatusTrackingService.update_order_status(
    order=order,
    new_status='driver_assigned',
    updated_by=vendor,
    notes='Driver John assigned',
    driver_id=123
)

# Automatic validation, driver assignment, and history creation
# Truck availability automatically managed
```

### **4. Role-Based Status Updates**

```python
# Customers can only cancel orders
OrderStatusTrackingService.update_order_status(
    order=order,
    new_status='cancelled',  # ✅ Allowed for customers
    updated_by=customer
)

# Vendors can progress orders
OrderStatusTrackingService.update_order_status(
    order=order,
    new_status='picked_up',  # ✅ Allowed for vendors
    updated_by=vendor,
    latitude=Decimal('28.6139'),
    longitude=Decimal('77.2090')
)
```

---

## 🔄 **Automatic Status Workflow**

```
created → confirmed → driver_assigned → pickup → picked_up → in_transit → delivered → completed
    ↓         ↓              ↓            ↓          ↓            ↓           ↓         
cancelled  cancelled      cancelled   cancelled     ✗            ✗           ✗
```

**Automatic Actions:**
- `driver_assigned`: Links driver to order
- `picked_up`: Sets actual_pickup_date, records actual_weight
- `delivered`: Sets actual_delivery_date
- `completed`: Frees truck (availability_status = 'available'), marks OTP verified
- `cancelled`: Frees truck immediately

---

## 📊 **Analytics & Reporting**

```python
from orders.services import OrderAnalyticsService

analytics = OrderAnalyticsService.get_order_analytics(order)

# Get comprehensive order insights:
# - Status timeline
# - Document count
# - Estimated vs actual dates/weights
# - Performance metrics
```

---

## 🛡️ **Built-in Validations**

### **Business Rules:**
- ✅ Only customers can create orders from their quotations
- ✅ Only active quotations can become orders
- ✅ No duplicate orders from same quotation
- ✅ Quotation expiry validation
- ✅ Role-based status update permissions

### **Status Transition Rules:**
- ✅ Invalid transitions automatically blocked
- ✅ Final states (completed/cancelled) prevent further changes
- ✅ User permissions validated for each status
- ✅ Ownership validation (customers can only modify their orders)

---

## 🔧 **Integration Points**

### **Updated Files:**

1. **`orders/services.py`** - New centralized services
2. **`quotations/services.py`** - Fixed accept_negotiation method
3. **`orders/api/serializers.py`** - Uses OrderCreationService
4. **`orders/api/views.py`** - Uses OrderStatusTrackingService

### **API Endpoints Now Use Services:**

- `POST /api/orders/` - Uses OrderCreationService
- `POST /api/orders/{id}/status/` - Uses OrderStatusTrackingService
- `POST /api/quotations/negotiations/{id}/accept/` - Uses QuotationStatusService

---

## 🧪 **Testing the New System**

### **Management Command Demo:**

```bash
# Demo order creation from quotation
python manage.py demo_order_automation --quotation-id=1

# Demo negotiation acceptance
python manage.py demo_order_automation --negotiation-id=1

# See available quotations/negotiations
python manage.py demo_order_automation
```

### **Expected Output:**
```
🚛 Order Management System Demo

📋 Creating Order from Quotation...
✅ Order #ORD-2024-001234 created successfully!
   Order ID: 456
   Delivery OTP: 123456
   Status: created
   Truck Updated: True

📊 Demonstrating Status Transitions...
   🔄 created → confirmed
   🔄 confirmed → driver_assigned
      📌 driver_assigned: John Doe
   🔄 driver_assigned → pickup
   🔄 pickup → picked_up
      📌 picked_up_at: 2024-01-15 10:30:00
   🔄 picked_up → in_transit
   🔄 in_transit → delivered
      📌 delivered_at: 2024-01-15 18:45:00
   🔄 delivered → completed
      📌 truck_freed: True
      📌 otp_verified: True

📈 Order Analytics:
   📦 Order: #ORD-2024-001234
   📊 Status Changes: 8
   ✅ Completed: True
   📄 Documents: 0
```

---

## 💡 **Key Benefits**

1. **🎯 Centralized Logic**: All order business logic in dedicated services
2. **🔒 Automatic Validation**: Role-based permissions and business rules enforced
3. **📈 Complete Tracking**: Every status change automatically recorded with context
4. **🚛 Smart Truck Management**: Truck availability automatically updated
5. **🔧 Easy Maintenance**: Single point of change for order workflow
6. **📊 Rich Analytics**: Comprehensive order performance insights
7. **🧪 Testable**: Services can be easily unit tested
8. **🔄 Consistent API**: Standardized responses across all endpoints

---

## 🚀 **Next Steps**

1. **Test the new services** with your existing data
2. **Run the demo command** to see the automation in action
3. **Update your frontend** to handle the new response formats
4. **Add more business rules** as needed using the established patterns
5. **Extend analytics** with custom metrics for your business needs

The new system provides a robust foundation for order management that will scale with your business growth! 🎉
