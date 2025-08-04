# 🚚 Uber for Transport

## 📄 Overview

This platform is a digital marketplace connecting customers seeking truck transport services with vendors who own trucks and drivers. It provides an experience similar to Uber but focused on logistics and transportation.

## 👥 User Roles

There are **two main user roles:**

* **Customers** (individuals or businesses needing transport)
* **Vendors** (truck operators managing fleets and drivers)
* **Admin** (track and monitor everything)

---

## 🎯 Features

### 🎫 Features for All Users (No Authentication Required)

* **Search & List Trucks**

  * Users can enter pickup and arrival locations to view available trucks.
  * Basic truck details shown (capacity, estimated pricing, vendor name).

---

### 🙍‍♂️ Customer Features (With Authentication)

* **Ask for Quotations**

  * Request quotations from multiple vendors for selected trucks.
  * Specify pickup/arrival dates and locations.
* **Renegotiate Quotations**

  * Negotiate price adjustments with vendors.
* **Track Orders**

  * Live tracking of shipment status: Order Created → Pickup → Shipped → Arrived.
* **Download Invoice**

  * Generate and download invoices for completed orders.

---

### 🧑‍🔧 Vendor Features (With Authentication)

* **Add Trucks**

  * Register trucks with details: type, capacity, availability, photos.
* **Add Drivers**

  * Create driver profiles linked to specific trucks.
* **Send Quotations**

  * Provide pricing proposals to customer requests.
* **Renegotiate Quotations**

  * Respond to negotiation requests with revised pricing.
* **Accept Quotations**

  * Final confirmation of agreed pricing.
* **Track and Update Order Status**

  * Update each stage: Pickup, Shipped, Arrived.

---

## 🛠️ Implementation Plan

Below is a **step-by-step breakdown** aligned with the flowchart you shared:

---

### 1️⃣ **Authentication and Authorization**

* Use JWT-based authentication.
* Roles:

  * `customer`
  * `vendor`
  * `admin`
* Access control middleware to restrict APIs based on role.

---

### 2️⃣ **Truck and Driver Management (Vendor)**

* **Add Truck**

  * API: `POST /api/vendor/trucks`
  * Fields: truck type, capacity, images, registration number.
* **Add Driver**

  * API: `POST /api/vendor/drivers`
  * Fields: name, license number, truck assignment.

---

### 3️⃣ **Truck Search (Public)**

* **Search Truck**

  * API: `GET /api/trucks/search`
  * Params: pickup location, arrival location.
  * Returns: list of available trucks with vendor contact info.

---

### 4️⃣ **Quotation Process (Customer & Vendor)**

* **Ask for Quotation**

  * API: `POST /api/quotations/request`
  * Payload: truck ID, pickup/arrival location and date.
  * Triggers creation of *Order Request*.
* **Renegotiate Quotation**

  * API: `POST /api/quotations/{id}/renegotiate`
  * Allows negotiation of price and terms.
* **Accept Quotation**

  * API: `POST /api/quotations/{id}/accept`
  * Triggers:

    * Order creation
    * Payment Request

---

### 5️⃣ **Order Lifecycle**

* **Order Created**

  * Status transitions: Created → Pickup → Shipped → Arrived.
* **Assign Driver**

  * Vendor assigns driver to the order.
* **Update Shipment Status**

  * API: `PATCH /api/orders/{id}/status`
  * Status options:

    * Order Pickup
    * Order Shipped
    * Order Arrived
* **Track Order**

  * Customer can poll or receive websocket updates.
* **Generate Invoice**

  * API: `GET /api/orders/{id}/invoice`

---

### 6️⃣ **Payments**

* **Payment Requested**

  * Generated upon quotation acceptance and on delivery arrival.
* **Payment Completion**

  * Customer completes payment via integrated gateway.
  * API: `POST /api/payments/complete`
* **Invoice Download**

  * PDF invoice available post-payment.

---

## 🚀 Milestones

| Milestone                    | Tasks                                                                                       |
| ---------------------------- | ------------------------------------------------------------------------------------------- |
| **Phase 1: Core APIs**       | Authentication, Truck Search, Truck/Driver CRUD                                             |
| **Phase 2: Quotations**      | Quotation Requests, Renegotiation, Acceptance, Order Creation                               |
| **Phase 3: Order Tracking**  | Shipment lifecycle APIs, Driver Assignment, Realtime tracking                               |
| **Phase 4: Payments**        | Payment Gateway integration, Invoice generation, Payment completion flow                    |
| **Phase 5: QA & Deployment** | End-to-end testing, Dockerizing                                             |

---

## 🧭 Additional Notes

* Use role-based permissions.
* Ensure secure storage of driver/truck data.
* Notifications (email/SMS) can be added post-MVP.
* All date/time fields should be timezone-aware.
* Implement soft deletes for truck/driver records.

---