from django.urls import path
from quotations.api import views, route_views

urlpatterns = [
    # LEGACY CART/QUOTATION APIs (Deprecated - for backward compatibility)
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/add/', views.AddToCartView.as_view(), name='add-to-cart'),
    path('cart/items/<int:item_id>/update/', views.UpdateCartItemView.as_view(), name='update-cart-item'),
    path('cart/items/<int:item_id>/remove/', views.RemoveFromCartView.as_view(), name='remove-from-cart'),
    path('cart/clear/', views.ClearCartView.as_view(), name='clear-cart'),
    
    # LEGACY Customer APIs (Deprecated)
    path('customer/requests/', views.CustomerQuotationRequestsView.as_view(), name='customer-quotation-requests'),
    path('customer/quotations/', views.CustomerQuotationsView.as_view(), name='customer-quotations'),
    path('requests/create/', views.QuotationRequestCreateView.as_view(), name='create-quotation-request'),
    path('requests/<int:pk>/', views.QuotationRequestDetailView.as_view(), name='quotation-request-detail'),
    path('requests/<int:request_id>/quotations/', views.QuotationListView.as_view(), name='quotations-for-request'),
    path('<int:quotation_id>/accept/', views.QuotationAcceptView.as_view(), name='accept-quotation'),
    path('<int:quotation_id>/reject/', views.QuotationRejectView.as_view(), name='reject-quotation'),
    
    # LEGACY Vendor APIs (Deprecated)
    path('vendor/requests/', views.VendorQuotationRequestsView.as_view(), name='vendor-quotation-requests'),
    path('vendor/quotations/', views.VendorQuotationsView.as_view(), name='vendor-quotations'),
    path('create/', views.QuotationCreateView.as_view(), name='create-quotation'),
    
    # LEGACY Common APIs (Deprecated)
    path('<int:pk>/', views.QuotationDetailView.as_view(), name='quotation-detail'),
    
    # LEGACY Negotiation APIs (Deprecated)
    path('negotiations/create/', views.NegotiationCreateView.as_view(), name='create-negotiation'),
    path('<int:quotation_id>/negotiations/', views.NegotiationListView.as_view(), name='quotation-negotiations'),
    path('negotiations/<int:negotiation_id>/accept/', views.AcceptNegotiationView.as_view(), name='accept-negotiation'),
]
