from django.urls import path
from payments.api import views

urlpatterns = [
    # Payment Management
    path('create/', views.PaymentCreateView.as_view(), name='create-payment'),
    path('', views.PaymentListView.as_view(), name='payment-list'),
    path('<int:pk>/', views.PaymentDetailView.as_view(), name='payment-detail'),
    path('initiate/', views.PaymentInitiateView.as_view(), name='initiate-payment'),
    path('complete/', views.PaymentCompleteView.as_view(), name='complete-payment'),
    path('order/<int:order_id>/', views.OrderPaymentsView.as_view(), name='order-payments'),
    
    # Payment History
    path('<int:payment_id>/history/', views.PaymentHistoryView.as_view(), name='payment-history'),
    
    # Invoice Management
    path('invoices/create/', views.InvoiceCreateView.as_view(), name='create-invoice'),
    path('invoices/', views.InvoiceListView.as_view(), name='invoice-list'),
    path('invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice-detail'),
    path('invoices/<int:invoice_id>/download/', views.InvoiceDownloadView.as_view(), name='download-invoice'),
    path('invoices/<int:invoice_id>/generate/', views.GenerateInvoiceView.as_view(), name='generate-invoice'),
    
    # Statistics
    path('vendor/stats/', views.PaymentStatsView.as_view(), name='payment-stats'),
]
