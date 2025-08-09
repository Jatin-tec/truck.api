from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import models
from django.utils import timezone
from django.http import HttpResponse
from payments.models import Payment, Invoice, PaymentHistory
from payments.api.serializers import (
    PaymentSerializer, PaymentCreateSerializer, PaymentStatusUpdateSerializer,
    InvoiceSerializer, InvoiceCreateSerializer, PaymentHistorySerializer,
    PaymentInitiateSerializer, PaymentCompleteSerializer
)
from project.utils import success_response, error_response, validation_error_response, StandardizedResponseMixin
from project.permissions import IsCustomer, IsVendor, IsCustomerOrVendor

# Payment Views
class PaymentCreateView(StandardizedResponseMixin, generics.CreateAPIView):
    """Customer creates a payment"""
    serializer_class = PaymentCreateSerializer
    permission_classes = [IsCustomer]

class PaymentListView(StandardizedResponseMixin, generics.ListAPIView):
    """List payments for user"""
    serializer_class = PaymentSerializer
    permission_classes = [IsCustomerOrVendor]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'customer':
            return Payment.objects.filter(order__customer=user).order_by('-created_at')
        else:  # vendor
            return Payment.objects.filter(order__vendor=user).order_by('-created_at')

class PaymentDetailView(StandardizedResponseMixin, generics.RetrieveAPIView):
    """Get payment details"""
    serializer_class = PaymentSerializer
    permission_classes = [IsCustomerOrVendor]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'customer':
            return Payment.objects.filter(order__customer=user)
        else:  # vendor
            return Payment.objects.filter(order__vendor=user)

class PaymentInitiateView(APIView):
    """Initiate payment with gateway"""
    permission_classes = [IsCustomer]
    
    def post(self, request):
        serializer = PaymentInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        payment_id = serializer.validated_data['payment_id']
        gateway = serializer.validated_data['gateway']
        
        try:
            payment = Payment.objects.get(
                payment_id=payment_id,
                order__customer=request.user,
                status='pending'
            )
            
            # Update payment status and gateway info
            payment.status = 'initiated'
            payment.gateway_name = gateway
            payment.initiated_at = timezone.now()
            payment.save()
            
            # Create payment history
            PaymentHistory.objects.create(
                payment=payment,
                previous_status='pending',
                new_status='initiated',
                notes=f'Payment initiated with {gateway}'
            )
            
            # Here you would integrate with actual payment gateway
            # For now, we'll return a mock response
            gateway_response = {
                'gateway_order_id': f"{gateway}_{payment_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}",
                'amount': float(payment.amount),
                'currency': 'INR',
                'redirect_url': f'https://checkout.{gateway}.com/mock-payment'
            }
            
            return Response({
                'message': 'Payment initiated successfully',
                'payment_id': payment.payment_id,
                'gateway_response': gateway_response
            })
            
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found or cannot be initiated'},
                status=status.HTTP_404_NOT_FOUND
            )

class PaymentCompleteView(APIView):
    """Complete payment (webhook from gateway)"""
    permission_classes = []  # No permission required for webhook
    
    def post(self, request):
        serializer = PaymentCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        payment_id = data['payment_id']
        
        try:
            payment = Payment.objects.get(
                payment_id=payment_id,
                status='initiated'
            )
            
            previous_status = payment.status
            payment.status = data['status']
            payment.gateway_transaction_id = data['gateway_transaction_id']
            payment.gateway_response = data['gateway_response']
            
            if data['status'] == 'completed':
                payment.completed_at = timezone.now()
            elif data['status'] == 'failed':
                payment.failed_at = timezone.now()
                payment.failure_reason = data.get('failure_reason', '')
            
            payment.save()
            
            # Create payment history
            PaymentHistory.objects.create(
                payment=payment,
                previous_status=previous_status,
                new_status=data['status'],
                notes=f"Payment {data['status']} via gateway"
            )
            
            # If payment is completed and it's full payment, update order status
            if data['status'] == 'completed' and payment.payment_type == 'full':
                order = payment.order
                order.status = 'confirmed'
                order.save()
            
            return Response({'message': f"Payment {data['status']} successfully"})
            
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class OrderPaymentsView(generics.ListAPIView):
    """List payments for a specific order"""
    serializer_class = PaymentSerializer
    permission_classes = [IsCustomerOrVendor]
    
    def get_queryset(self):
        order_id = self.kwargs['order_id']
        user = self.request.user
        
        # Verify user has access to this order
        from orders.models import Order
        try:
            if user.role == 'customer':
                order = Order.objects.get(id=order_id, customer=user)
            else:  # vendor
                order = Order.objects.get(id=order_id, vendor=user)
        except Order.DoesNotExist:
            return Payment.objects.none()
        
        return Payment.objects.filter(order_id=order_id).order_by('-created_at')

# Invoice Views
class InvoiceCreateView(generics.CreateAPIView):
    """Vendor creates an invoice"""
    serializer_class = InvoiceCreateSerializer
    permission_classes = [IsVendor]

class InvoiceListView(generics.ListAPIView):
    """List invoices for user"""
    serializer_class = InvoiceSerializer
    permission_classes = [IsCustomerOrVendor]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'customer':
            return Invoice.objects.filter(order__customer=user).order_by('-created_at')
        else:  # vendor
            return Invoice.objects.filter(order__vendor=user).order_by('-created_at')

class InvoiceDetailView(generics.RetrieveAPIView):
    """Get invoice details"""
    serializer_class = InvoiceSerializer
    permission_classes = [IsCustomerOrVendor]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'customer':
            return Invoice.objects.filter(order__customer=user)
        else:  # vendor
            return Invoice.objects.filter(order__vendor=user)

class InvoiceDownloadView(APIView):
    """Download invoice PDF"""
    permission_classes = [IsCustomerOrVendor]
    
    def get(self, request, invoice_id):
        user = request.user
        
        try:
            if user.role == 'customer':
                invoice = Invoice.objects.get(id=invoice_id, order__customer=user)
            else:  # vendor
                invoice = Invoice.objects.get(id=invoice_id, order__vendor=user)
            
            if not invoice.invoice_file:
                return Response(
                    {'error': 'Invoice file not generated yet'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Return file response
            response = HttpResponse(
                invoice.invoice_file.read(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="{invoice.invoice_number}.pdf"'
            return response
            
        except Invoice.DoesNotExist:
            return Response(
                {'error': 'Invoice not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class GenerateInvoiceView(APIView):
    """Generate invoice PDF (vendor only)"""
    permission_classes = [IsVendor]
    
    def post(self, request, invoice_id):
        try:
            invoice = Invoice.objects.get(
                id=invoice_id,
                order__vendor=request.user,
                is_generated=False
            )
            
            # Here you would generate the actual PDF
            # For now, we'll just mark it as generated
            invoice.is_generated = True
            invoice.generated_at = timezone.now()
            # invoice.invoice_file = generated_pdf_file  # Save the generated PDF
            invoice.save()
            
            return Response({
                'message': 'Invoice generated successfully',
                'invoice_number': invoice.invoice_number
            })
            
        except Invoice.DoesNotExist:
            return Response(
                {'error': 'Invoice not found or already generated'},
                status=status.HTTP_404_NOT_FOUND
            )

# Payment History
class PaymentHistoryView(generics.ListAPIView):
    """Get payment history"""
    serializer_class = PaymentHistorySerializer
    permission_classes = [IsCustomerOrVendor]
    
    def get_queryset(self):
        payment_id = self.kwargs['payment_id']
        user = self.request.user
        
        # Verify user has access to this payment
        try:
            if user.role == 'customer':
                payment = Payment.objects.get(id=payment_id, order__customer=user)
            else:  # vendor
                payment = Payment.objects.get(id=payment_id, order__vendor=user)
        except Payment.DoesNotExist:
            return PaymentHistory.objects.none()
        
        return PaymentHistory.objects.filter(payment_id=payment_id).order_by('timestamp')

# Payment Statistics
class PaymentStatsView(APIView):
    """Get payment statistics for vendor"""
    permission_classes = [IsVendor]
    
    def get(self, request):
        vendor = request.user
        
        # Get payment statistics
        stats = Payment.objects.filter(order__vendor=vendor).aggregate(
            total_payments=models.Count('id'),
            total_amount=models.Sum('amount', filter=models.Q(status='completed')),
            pending_amount=models.Sum('amount', filter=models.Q(status='pending')),
            failed_amount=models.Sum('amount', filter=models.Q(status='failed'))
        )
        
        # Get monthly statistics
        from django.db.models import TruncMonth
        monthly_stats = Payment.objects.filter(
            order__vendor=vendor,
            status='completed'
        ).annotate(
            month=TruncMonth('completed_at')
        ).values('month').annotate(
            total=models.Sum('amount'),
            count=models.Count('id')
        ).order_by('month')
        
        return Response({
            'total_statistics': {
                'total_payments': stats['total_payments'] or 0,
                'total_amount': float(stats['total_amount'] or 0),
                'pending_amount': float(stats['pending_amount'] or 0),
                'failed_amount': float(stats['failed_amount'] or 0)
            },
            'monthly_statistics': [
                {
                    'month': item['month'].strftime('%Y-%m'),
                    'total_amount': float(item['total']),
                    'payment_count': item['count']
                }
                for item in monthly_stats
            ]
        })
