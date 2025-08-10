from django.urls import path
from quotations.api import views

urlpatterns = [
    # QUOTATION CREATION FLOW
    
    # Customer APIs
    path('customer/requests/', views.CustomerQuotationRequestsView.as_view(), name='customer-quotation-requests'),
    path('customer/quotations/', views.CustomerQuotationsView.as_view(), name='customer-quotations'),

    path('requests/create/', views.QuotationCreateView.as_view(), name='new-create-quotation'),
    path('requests/<int:pk>/', views.QuotationRequestDetailView.as_view(), name='quotation-request-detail'),
    path('requests/<int:request_id>/quotations/', views.QuotationListView.as_view(), name='quotations-for-request'),

    path('<int:quotation_id>/accept/', views.QuotationAcceptView.as_view(), name='accept-quotation'),
    path('<int:quotation_id>/reject/', views.QuotationRejectView.as_view(), name='reject-quotation'),

    # Vendor APIs
    path('vendor/requests/', views.VendorQuotationRequestsView.as_view(), name='vendor-quotation-requests'),
    path('vendor/quotations/', views.VendorQuotationsView.as_view(), name='vendor-quotations'),
    # path('vendor/respond/', views.VendorQuotationResponseView.as_view(), name='vendor-quotation-response'),

    # Common APIs
    path('<int:pk>/', views.QuotationDetailView.as_view(), name='quotation-detail'),

    # Negotiation APIs
    path('<int:quotation_id>/negotiations/', views.NegotiationListView.as_view(), name='negotiation-list'),
    path('<int:quotation_id>/negotiations/create/', views.NegotiationCreateView.as_view(), name='create-negotiation'),
    path('negotiations/<int:negotiation_id>/accept/', views.AcceptNegotiationView.as_view(), name='accept-negotiation'),
]
