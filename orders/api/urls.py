from django.urls import path
from orders.api import views

urlpatterns = [
    # Order Creation
    path('create/', views.OrderCreateView.as_view(), name='create-order'),

    # Order Listing and Details
    path('customer/orders/', views.CustomerOrdersView.as_view(), name='customer-orders'),
    path('vendor/orders/', views.VendorOrdersView.as_view(), name='vendor-orders'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),

    # Order Management (Vendor)
    path('<int:order_id>/update-status/', views.OrderStatusUpdateView.as_view(), name='update-order-status'),
    path('<int:order_id>/assign-driver/', views.AssignDriverView.as_view(), name='assign-driver'),

    # Order Tracking
    # path('<int:order_id>/tracking/', views.OrderTrackingView.as_view(), name='order-tracking'),
    # path('<int:order_id>/update-location/', views.UpdateOrderLocationView.as_view(), name='update-order-location'),
    path('<int:order_id>/status-history/', views.OrderStatusHistoryView.as_view(), name='order-status-history'),

    # Delivery Verification
    path('<int:order_id>/verify-delivery/', views.DeliveryVerificationView.as_view(), name='verify-delivery'),

    # Document Management
    path('<int:order_id>/documents/', views.OrderDocumentListView.as_view(), name='order-documents'),
    path('documents/upload/', views.OrderDocumentUploadView.as_view(), name='upload-order-document'),
]
