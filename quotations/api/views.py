from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from project.utils import (
    success_response, error_response, validation_error_response, 
    StandardizedResponseMixin
)
from project.permissions import IsCustomer, IsVendor, IsCustomerOrVendor
from quotations.models import (
    QuotationRequest, Quotation, QuotationNegotiation
)
from quotations.api.serializers import (
    QuotationRequestSerializer, QuotationSerializer,
    QuotationCreateSerializer, QuotationCreateV2Serializer, 
    QuotationRequestDetailSerializer
)


class CustomerQuotationRequestsView(StandardizedResponseMixin, generics.ListAPIView):
    """List quotation requests for authenticated customer"""
    serializer_class = QuotationRequestSerializer
    permission_classes = [IsCustomer]
    
    def get_queryset(self):
        return QuotationRequest.objects.filter(
            customer=self.request.user,
            is_active=True
        ).order_by('-created_at')


class QuotationRequestDetailView(StandardizedResponseMixin, generics.RetrieveAPIView):
    """Get details of a specific quotation request"""
    serializer_class = QuotationRequestDetailSerializer
    permission_classes = [IsCustomerOrVendor]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'customer':
            return QuotationRequest.objects.filter(customer=user, is_active=True)
        else:  # vendor
            return QuotationRequest.objects.filter(vendor=user, is_active=True)


# Quotation Views
class VendorQuotationRequestsView(StandardizedResponseMixin, generics.ListAPIView):
    """List quotation requests for vendor"""
    serializer_class = QuotationRequestSerializer
    permission_classes = [IsVendor]
    
    def get_queryset(self):
        return QuotationRequest.objects.filter(
            vendor=self.request.user,
            is_active=True
        ).order_by('-created_at')


class QuotationCreateView(APIView, StandardizedResponseMixin):
    """
    Create quotation with the new flow:
    1. Create/find quotation request based on search parameters
    2. Add quotation to that request
    
    Supports both legacy format and new exact format from request body
    """
    permission_classes = [IsCustomer]

    def post(self, request):
        """Create quotation using the new flow"""
        
        # Determine which serializer to use based on request format
        if 'vendor_id' in request.data and 'origin_pincode' in request.data:
            # New format - exact match to provided request
            serializer = QuotationCreateV2Serializer(
                data=request.data, 
                context={'request': request}
            )
        else:
            # Legacy format with searchParams structure
            serializer = QuotationCreateSerializer(
                data=request.data, 
                context={'request': request}
            )
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        try:
            # Create quotation and quotation request
            result = serializer.save()
            
            quotation_request = result['quotation_request']
            quotation = result['quotation']
            created_new_request = result['created_new_request']
            quotation_updated = result.get('quotation_updated', False)
            
            # Prepare response message
            if created_new_request:
                if quotation_updated:
                    message = f"New quotation request created and existing quotation updated for route {quotation_request.origin_pincode} to {quotation_request.destination_pincode}"
                else:
                    message = f"New quotation request created and quotation added for route {quotation_request.origin_pincode} to {quotation_request.destination_pincode}"
            else:
                if quotation_updated:
                    message = f"Existing quotation updated for route {quotation_request.origin_pincode} to {quotation_request.destination_pincode}"
                else:
                    message = f"Quotation added to existing request for route {quotation_request.origin_pincode} to {quotation_request.destination_pincode}"
            
            # Prepare response data
            response_data = {
                'quotation_request': {
                    'id': quotation_request.id,
                    'origin_pincode': quotation_request.origin_pincode,
                    'destination_pincode': quotation_request.destination_pincode,
                    'pickup_date': quotation_request.pickup_date.isoformat(),
                    'drop_date': quotation_request.drop_date.isoformat(),
                    'weight': str(quotation_request.weight),
                    'weight_unit': quotation_request.weight_unit,
                    'vehicle_type': quotation_request.vehicle_type,
                    'urgency_level': quotation_request.urgency_level,
                    'total_quotations': quotation_request.get_total_quotations(),
                    'created_at': quotation_request.created_at.isoformat(),
                },
                'quotation': {
                    'id': quotation.id,
                    'vendor_id': quotation.vendor.id,
                    'vendor_name': quotation.vendor_name,
                    'items': quotation.items,
                    'total_amount': str(quotation.total_amount),
                    'status': quotation.status,
                    'validity_hours': quotation.validity_hours,
                    'created_at': quotation.created_at.isoformat(),
                    'updated_at': quotation.updated_at.isoformat(),
                },
                'created_new_request': created_new_request,
                'quotation_updated': quotation_updated,
                'message': message
            }
            
            return success_response(
                data=response_data,
                message=message,
                status_code=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return error_response(
                error=f"Failed to create quotation: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class QuotationListView(StandardizedResponseMixin, generics.ListAPIView):
    """List quotations for a specific quotation request"""
    serializer_class = QuotationSerializer
    permission_classes = [IsCustomerOrVendor]
    
    def get_queryset(self):
        request_id = self.kwargs['request_id']
        user = self.request.user
        
        quotations = Quotation.objects.filter(
            quotation_request_id=request_id,
            is_active=True
        )
        
        # Filter based on user role
        if user.role == 'customer':
            quotations = quotations.filter(quotation_request__customer=user)
        elif user.role == 'vendor':
            quotations = quotations.filter(vendor=user)
            
        return quotations.order_by('-created_at')


class QuotationDetailView(StandardizedResponseMixin, generics.RetrieveAPIView):
    """Get details of a specific quotation"""
    serializer_class = QuotationSerializer
    permission_classes = [IsCustomerOrVendor]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'customer':
            return Quotation.objects.filter(
                quotation_request__customer=user,
                is_active=True
            )
        else:  # vendor
            return Quotation.objects.filter(vendor=user, is_active=True)


class VendorQuotationsView(StandardizedResponseMixin, generics.ListAPIView):
    """List all quotations created by vendor"""
    serializer_class = QuotationSerializer
    permission_classes = [IsVendor]
    
    def get_queryset(self):
        return Quotation.objects.filter(
            vendor=self.request.user,
            is_active=True
        ).order_by('-created_at')


class CustomerQuotationsView(StandardizedResponseMixin, generics.ListAPIView):
    """List all quotations received by customer"""
    serializer_class = QuotationSerializer
    permission_classes = [IsCustomer]
    
    def get_queryset(self):
        return Quotation.objects.filter(
            quotation_request__customer=self.request.user,
            is_active=True
        ).order_by('-created_at')


# Quotation Status Management
class QuotationAcceptView(APIView):
    """Customer accepts a quotation"""
    permission_classes = [IsCustomer]
    
    def post(self, request, quotation_id):
        try:
            quotation = Quotation.objects.get(
                id=quotation_id,
                quotation_request__customer=request.user,
                status__in=['sent', 'negotiating'],
                is_active=True
            )
            
            quotation.status = 'accepted'
            quotation.save()
            
            # Mark other quotations for the same request as rejected
            Quotation.objects.filter(
                quotation_request=quotation.quotation_request,
                is_active=True
            ).exclude(id=quotation.id).update(status='rejected')
            
            return Response({
                'message': 'Quotation accepted successfully',
                'quotation_id': quotation.id
            })
            
        except Quotation.DoesNotExist:
            return Response(
                {'error': 'Quotation not found or cannot be accepted'},
                status=status.HTTP_404_NOT_FOUND
            )


class QuotationRejectView(APIView):
    """Customer rejects a quotation"""
    permission_classes = [IsCustomer]
    
    def post(self, request, quotation_id):
        try:
            quotation = Quotation.objects.get(
                id=quotation_id,
                quotation_request__customer=request.user,
                status__in=['sent', 'negotiating'],
                is_active=True
            )
            
            quotation.status = 'rejected'
            quotation.save()
            
            return Response({'message': 'Quotation rejected successfully'})
            
        except Quotation.DoesNotExist:
            return Response(
                {'error': 'Quotation not found or cannot be rejected'},
                status=status.HTTP_404_NOT_FOUND
            )


# Negotiation Views
# class NegotiationCreateView(generics.CreateAPIView):
#     """Create a negotiation for a quotation"""
#     serializer_class = NegotiationCreateSerializer
#     permission_classes = [IsCustomerOrVendor]


# class NegotiationListView(generics.ListAPIView):
#     """List negotiations for a specific quotation"""
#     serializer_class = QuotationNegotiationSerializer
#     permission_classes = [IsCustomerOrVendor]
    
#     def get_queryset(self):
#         quotation_id = self.kwargs['quotation_id']
#         user = self.request.user
        
#         # Ensure user has access to this quotation
#         try:
#             if user.role == 'customer':
#                 quotation = Quotation.objects.get(
#                     id=quotation_id,
#                     quotation_request__customer=user
#                 )
#             else:  # vendor
#                 quotation = Quotation.objects.get(
#                     id=quotation_id,
#                     vendor=user
#                 )
#         except Quotation.DoesNotExist:
#             return QuotationNegotiation.objects.none()
        
#         return QuotationNegotiation.objects.filter(
#             quotation_id=quotation_id
#         ).order_by('created_at')


class AcceptNegotiationView(APIView):
    """Accept a negotiation and update quotation"""
    permission_classes = [IsCustomerOrVendor]
    
    def post(self, request, negotiation_id):
        try:
            negotiation = QuotationNegotiation.objects.get(id=negotiation_id)
            quotation = negotiation.quotation
            user = request.user
            
            # Check if user is authorized to accept this negotiation
            if user.role == 'customer' and user != quotation.quotation_request.customer:
                raise permissions.PermissionDenied()
            elif user.role == 'vendor' and user != quotation.vendor:
                raise permissions.PermissionDenied()
            
            # Check if the negotiation was initiated by the other party
            if ((user.role == 'customer' and negotiation.initiated_by == 'customer') or
                (user.role == 'vendor' and negotiation.initiated_by == 'vendor')):
                return Response(
                    {'error': 'You cannot accept your own negotiation'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update quotation with negotiated values
            quotation.total_base_price = negotiation.proposed_base_price or quotation.total_base_price
            quotation.total_fuel_charges = negotiation.proposed_fuel_charges or quotation.total_fuel_charges
            quotation.total_toll_charges = negotiation.proposed_toll_charges or quotation.total_toll_charges
            quotation.total_loading_charges = negotiation.proposed_loading_charges or quotation.total_loading_charges
            quotation.total_unloading_charges = negotiation.proposed_unloading_charges or quotation.total_unloading_charges
            quotation.total_additional_charges = negotiation.proposed_additional_charges or quotation.total_additional_charges
            quotation.status = 'sent'  # Back to sent status after accepting negotiation
            quotation.save()  # This will recalculate total_amount
            
            return Response({
                'message': 'Negotiation accepted and quotation updated',
                'new_total_amount': quotation.total_amount
            })
            
        except QuotationNegotiation.DoesNotExist:
            return Response(
                {'error': 'Negotiation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
