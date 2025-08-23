from rest_framework import generics, status, permissions
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.exceptions import ValidationError

from project.utils import (
    success_response, error_response, validation_error_response, 
    StandardizedResponseMixin
)
from project.permissions import IsCustomer, IsVendor, IsCustomerOrVendor
from quotations.models import (
    QuotationRequest, Quotation, QuotationNegotiation
)
from quotations.services import QuotationService, QuotationStatusService, NegotiationService
from quotations.validators import BusinessRuleEngine
from quotations.enums import ErrorMessages, ResponseMessages
from quotations.api.serializers import (
    QuotationRequestSerializer, QuotationSerializer,
    QuotationCreateSerializer, 
    QuotationRequestDetailSerializer, NegotiationCreateSerializer,
    QuotationNegotiationSerializer
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
        else:
            # Vendors can see all active requests to decide which ones to quote for
            return QuotationRequest.objects.filter(is_active=True)


# Quotation Views
class VendorQuotationRequestsView(StandardizedResponseMixin, generics.ListAPIView):
    """List quotation requests for vendor"""
    serializer_class = QuotationRequestSerializer
    permission_classes = [IsVendor]
    
    def get_queryset(self):
        # Vendors can see all active requests to decide which ones to quote for
        return QuotationRequest.objects.filter(
            is_active=True
        ).order_by('-created_at')


class QuotationCreateView(APIView, StandardizedResponseMixin):
    """
    Customer creates quotation request for specific vendor with selected vehicle items
    This matches the TypeScript interface where customers select vendor and vehicles
    """
    permission_classes = [IsCustomer]

    def post(self, request):
        """Create quotation request with vendor and vehicle selection"""
        
        # Use the QuotationCreateSerializer which handles the actual frontend structure
        serializer = QuotationCreateSerializer(
            data=request.data, 
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        # try:
        # Create quotation request and quotation with vendor selection
        result = serializer.save()
        
        quotation_request = result['quotation_request']
        quotation = result['quotation']
        created_new_request = result['created_new_request']
        customer_negotiation = result.get('customer_negotiation')
        
        # Extract search params from the original request
        search_params = request.data.get('searchParams', {})
        
        # Prepare response message
        if created_new_request:
            message = f"Quotation request created for vendor {quotation.vendor_name} with selected vehicles"
        else:
            message = f"Updated quotation request for vendor {quotation.vendor_name}"
        
        # Prepare response data matching your TypeScript interface expectation
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
                'total_quotations': quotation_request.get_total_quotations(),
                'created_at': quotation_request.created_at.isoformat(),
            },
            'quotation': {
                'id': quotation.id,
                'vendor_id': quotation.vendor.id,
                'vendor_name': quotation.vendor_name,
                'items': [
                    {
                        'id': item.id,
                        'quantity': item.quantity,
                        'unit_price': str(item.unit_price),
                        'total_price': str(item.get_total_price()),
                        'vehicle_type': item.truck_type.name if item.truck_type else 'Unknown',
                        'truck_id': item.truck.id if item.truck else None,
                        'truck_type_id': item.truck_type.id if item.truck_type else None,
                        'estimated_delivery': item.estimated_delivery.isoformat() if item.estimated_delivery else None,
                        'special_instructions': item.special_instructions,
                        'pickup_locations': item.pickup_locations,
                        'drop_locations': item.drop_locations,
                    } for item in quotation.items.all()
                ],
                'total_amount': str(quotation.total_amount),
                'urgency_level': quotation.urgency_level,
                'status': quotation.status,
                'validity_hours': quotation.validity_hours,
                'created_at': quotation.created_at.isoformat(),
                'updated_at': quotation.updated_at.isoformat(),
            },
            'search_params': {
                'origin_pincode': search_params.get('originPinCode', quotation_request.origin_pincode),
                'destination_pincode': search_params.get('destinationPinCode', quotation_request.destination_pincode),
                'pickup_date': search_params.get('pickupDate', quotation_request.pickup_date.isoformat()),
                'drop_date': search_params.get('dropDate', quotation_request.drop_date.isoformat()),
                'weight': search_params.get('weight', str(quotation_request.weight)),
                'weight_unit': search_params.get('weightUnit', quotation_request.weight_unit),
                'vehicle_type': search_params.get('vehicleType', quotation_request.vehicle_type),
                'urgency_level': search_params.get('urgencyLevel', quotation_request.urgency_level),
            },
            'created_new_request': created_new_request,
            'message': message
        }
        
        # Add customer negotiation data
        if customer_negotiation:
            response_data['customer_negotiation'] = {
                'id': customer_negotiation.id,
                'initiated_by': customer_negotiation.initiated_by,
                'proposed_amount': str(customer_negotiation.proposed_amount),
                'message': customer_negotiation.message,
                'created_at': customer_negotiation.created_at.isoformat(),
            }
        
        return success_response(
            data=response_data,
            message=message,
            status_code=status.HTTP_201_CREATED
        )
            
        # except Exception as e:
        #     return error_response(
        #         error=f"Failed to create quotation request: {str(e)}",
        #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        #     )


# class VendorQuotationResponseView(APIView, StandardizedResponseMixin):
#     """
#     Vendor responds to customer's quotation request with their quote
#     This creates a vendor quotation response to an existing customer request
#     """
#     permission_classes = [IsVendor]

#     def post(self, request):
#         """Vendor creates a quotation response to customer's request"""
        
#         # Use QuotationCreateV2Serializer but modify it for vendor responses
#         serializer = QuotationCreateV2Serializer(
#             data=request.data, 
#             context={'request': request}
#         )
        
#         if not serializer.is_valid():
#             return validation_error_response(serializer.errors)
        
#         try:
#             # Create vendor's quotation response
#             result = serializer.save()
            
#             quotation_request = result['quotation_request']
#             quotation = result['quotation']
#             created_new_request = result['created_new_request']
#             quotation_updated = result.get('quotation_updated', False)
            
#             # Prepare response message
#             if quotation_updated:
#                 message = f"Updated your quotation for customer request {quotation_request.origin_pincode} to {quotation_request.destination_pincode}"
#             else:
#                 message = f"Quotation submitted for customer request {quotation_request.origin_pincode} to {quotation_request.destination_pincode}"
            
#             # Prepare response data
#             response_data = {
#                 'quotation_request': {
#                     'id': quotation_request.id,
#                     'customer_name': quotation_request.customer.name,
#                     'origin_pincode': quotation_request.origin_pincode,
#                     'destination_pincode': quotation_request.destination_pincode,
#                     'pickup_date': quotation_request.pickup_date.isoformat(),
#                     'drop_date': quotation_request.drop_date.isoformat(),
#                     'weight': str(quotation_request.weight),
#                     'weight_unit': quotation_request.weight_unit,
#                     'vehicle_type': quotation_request.vehicle_type,
#                     'urgency_level': quotation_request.urgency_level,
#                     'total_quotations': quotation_request.get_total_quotations(),
#                     'created_at': quotation_request.created_at.isoformat(),
#                 },
#                 'quotation': {
#                     'id': quotation.id,
#                     'vendor_name': quotation.vendor_name,
#                     'items': quotation.items,
#                     'total_amount': str(quotation.total_amount),
#                     'status': quotation.status,
#                     'validity_hours': quotation.validity_hours,
#                     'created_at': quotation.created_at.isoformat(),
#                     'updated_at': quotation.updated_at.isoformat(),
#                 },
#                 'quotation_updated': quotation_updated,
#                 'message': message
#             }
            
#             return success_response(
#                 data=response_data,
#                 message=message,
#                 status_code=status.HTTP_201_CREATED
#             )
            
#         except Exception as e:
#             return error_response(
#                 error=f"Failed to create vendor quotation: {str(e)}",
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )


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
    permission_classes = [AllowAny]
    
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
class QuotationAcceptView(APIView, StandardizedResponseMixin):
    """Customer accepts a quotation"""
    permission_classes = [IsCustomerOrVendor]
    
    def post(self, request, quotation_id):
        # try:
        if request.user.role == 'customer':
            quotation = Quotation.objects.get(
                id=quotation_id,
                quotation_request__customer=request.user,
                status__in=['sent', 'negotiating'],
                is_active=True
            )
        elif request.user.role == 'vendor':
            quotation = Quotation.objects.get(
                id=quotation_id,
                vendor=request.user,
                status__in=['sent', 'negotiating'],
                is_active=True
            )
        else:
            return error_response(
                error='Quotation not found or cannot be accepted',
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Use service layer for acceptance logic
        acceptance_result = QuotationStatusService.accept_quotation(quotation)
        
        response_data = {
            'quotation': {
                'id': quotation.id,
                'vendor_name': quotation.vendor_name,
                'original_amount': str(quotation.total_amount),
                'final_amount': str(acceptance_result['final_amount']),
                'status': quotation.status,
                'negotiations_count': quotation.negotiations.count(),
            },
            'quotation_request_id': quotation.quotation_request.id,
            'other_quotations_rejected': acceptance_result['rejected_count'],
            'has_negotiations': acceptance_result['had_negotiations']
        }
        
        message = ResponseMessages.QUOTATION_ACCEPTED.format(amount=acceptance_result['final_amount'])
        
        return success_response(
            data=response_data,
            message=message,
            status_code=status.HTTP_200_OK
        )
            
        # except Quotation.DoesNotExist:
        #     return error_response(
        #         error='Quotation not found or cannot be accepted',
        #         status_code=status.HTTP_404_NOT_FOUND
        #     )


class QuotationRejectView(APIView, StandardizedResponseMixin):
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
            
            # Update quotation status to rejected
            quotation.status = 'rejected'
            quotation.save()
            
            # Get some context about the rejection
            negotiations_count = quotation.negotiations.count()
            latest_negotiation = quotation.negotiations.order_by('-created_at').first()
            
            response_data = {
                'quotation': {
                    'id': quotation.id,
                    'vendor_name': quotation.vendor_name,
                    'original_amount': str(quotation.total_amount),
                    'status': quotation.status,
                    'negotiations_count': negotiations_count,
                },
                'quotation_request_id': quotation.quotation_request.id,
                'had_negotiations': negotiations_count > 0,
                'latest_negotiated_amount': str(latest_negotiation.proposed_amount) if latest_negotiation else None
            }
            
            return success_response(
                data=response_data,
                message=ResponseMessages.QUOTATION_REJECTED,
                status_code=status.HTTP_200_OK
            )
            
        except Quotation.DoesNotExist:
            return error_response(
                error='Quotation not found or cannot be rejected',
                status_code=status.HTTP_404_NOT_FOUND
            )


# Negotiation Views
class NegotiationCreateView(APIView, StandardizedResponseMixin):
    """Create a new negotiation offer"""
    permission_classes = [IsCustomerOrVendor]

    def post(self, request, quotation_id):
        """Create a negotiation offer for a quotation"""
        # try:
        # Get the quotation
        quotation = Quotation.objects.get(
            id=quotation_id,
            is_active=True
        )
        
        # Check permissions
        user = request.user
        if user.role == 'customer':
            # Customer can negotiate only their own quotation requests
            if quotation.quotation_request.customer != user:
                return error_response(
                    error=ErrorMessages.NOT_YOUR_QUOTATION,
                    status_code=status.HTTP_403_FORBIDDEN
                )
            initiated_by = 'customer'
        elif user.role == 'vendor':
            # Vendor can negotiate only their own quotations
            if quotation.vendor != user:
                return error_response(
                    error=ErrorMessages.NOT_YOUR_VENDOR_QUOTATION,
                    status_code=status.HTTP_403_FORBIDDEN
                )
            initiated_by = 'vendor'
        else:
            return error_response(
                error=ErrorMessages.ROLE_NOT_ALLOWED,
                status_code=status.HTTP_403_FORBIDDEN
            )

        # Validate request data
        serializer = NegotiationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        # Check business rules for negotiation
        can_negotiate, reason = NegotiationService.can_negotiate(quotation, initiated_by)
        if not can_negotiate:
            return error_response(
                error=reason,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Validate negotiation amount is reasonable
        proposed_amount = serializer.validated_data['proposed_amount']
        message = serializer.validated_data.get('message', '')
        negotiation = NegotiationService.create_negotiation(
            quotation, request.user.role,
            proposed_amount, message
        )
        if not negotiation:
            return error_response(
                error='Failed to create negotiation',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Create negotiation
        negotiation = QuotationNegotiation.objects.create(
            quotation=quotation,
            initiated_by=initiated_by,
            proposed_amount=serializer.validated_data['proposed_amount'],
            message=serializer.validated_data.get('message', ''),
            proposed_base_price=serializer.validated_data.get('proposed_base_price'),
            proposed_fuel_charges=serializer.validated_data.get('proposed_fuel_charges'),
            proposed_toll_charges=serializer.validated_data.get('proposed_toll_charges'),
            proposed_loading_charges=serializer.validated_data.get('proposed_loading_charges'),
            proposed_unloading_charges=serializer.validated_data.get('proposed_unloading_charges'),
            proposed_additional_charges=serializer.validated_data.get('proposed_additional_charges'),
        )

        # Update quotation status to negotiating
        quotation.status = 'negotiating'
        quotation.save()

        # Prepare response data
        response_data = {
            'negotiation': {
                'id': negotiation.id,
                'quotation_id': quotation.id,
                'initiated_by': negotiation.initiated_by,
                'proposed_amount': str(negotiation.proposed_amount),
                'message': negotiation.message,
                'proposed_base_price': str(negotiation.proposed_base_price) if negotiation.proposed_base_price else None,
                'proposed_fuel_charges': str(negotiation.proposed_fuel_charges) if negotiation.proposed_fuel_charges else None,
                'proposed_toll_charges': str(negotiation.proposed_toll_charges) if negotiation.proposed_toll_charges else None,
                'proposed_loading_charges': str(negotiation.proposed_loading_charges) if negotiation.proposed_loading_charges else None,
                'proposed_unloading_charges': str(negotiation.proposed_unloading_charges) if negotiation.proposed_unloading_charges else None,
                'proposed_additional_charges': str(negotiation.proposed_additional_charges) if negotiation.proposed_additional_charges else None,
                'created_at': negotiation.created_at.isoformat(),
            },
            'quotation_status': quotation.status
        }

        return success_response(
            data=response_data,
            message=ResponseMessages.NEGOTIATION_CREATED.format(initiator=initiated_by),
            status_code=status.HTTP_201_CREATED
        )

        # except Quotation.DoesNotExist:
        #     return error_response(
        #         error="Quotation not found",
        #         status_code=status.HTTP_404_NOT_FOUND
        #     )
        # except Exception as e:
        #     return error_response(
        #         error=f"Failed to create negotiation: {str(e)}",
        #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        #     )


class NegotiationListView(StandardizedResponseMixin, generics.ListAPIView):
    """List negotiations for a specific quotation"""
    serializer_class = QuotationNegotiationSerializer
    permission_classes = [IsCustomerOrVendor]
    
    def get_queryset(self):
        quotation_id = self.kwargs['quotation_id']
        user = self.request.user
        
        # Ensure user has access to this quotation
        try:
            if user.role == 'customer':
                quotation = Quotation.objects.get(
                    id=quotation_id,
                    quotation_request__customer=user
                )
            else:  # vendor
                quotation = Quotation.objects.get(
                    id=quotation_id,
                    vendor=user
                )
        except Quotation.DoesNotExist:
            return QuotationNegotiation.objects.none()
        
        return QuotationNegotiation.objects.filter(
            quotation_id=quotation_id
        ).order_by('created_at')

    def list(self, request, *args, **kwargs):
        """Override to add quotation info in response"""
        queryset = self.get_queryset()
        quotation_id = self.kwargs['quotation_id']
        
        if not queryset.exists():
            # Still try to get quotation info even if no negotiations
            try:
                user = self.request.user
                if user.role == 'customer':
                    quotation = Quotation.objects.get(
                        id=quotation_id,
                        quotation_request__customer=user
                    )
                else:  # vendor
                    quotation = Quotation.objects.get(
                        id=quotation_id,
                        vendor=user
                    )
                
                response_data = {
                    'quotation': {
                        'id': quotation.id,
                        'total_amount': str(quotation.total_amount),
                        'status': quotation.status,
                        'vendor_name': quotation.vendor_name,
                    },
                    'negotiations': [],
                    'total_negotiations': 0,
                    'can_negotiate': quotation.status in ['sent', 'negotiating']
                }
                
                return success_response(
                    data=response_data,
                    message=ResponseMessages.NO_NEGOTIATIONS_FOUND,
                    status_code=status.HTTP_200_OK
                )
                
            except Quotation.DoesNotExist:
                return error_response(
                    error="Quotation not found or not accessible",
                    status_code=status.HTTP_404_NOT_FOUND
                )
        
        # Get quotation info
        quotation = queryset.first().quotation
        
        # Serialize negotiations
        serializer = self.get_serializer(queryset, many=True)
        
        # Get latest negotiation to show current state
        latest_negotiation = queryset.order_by('-created_at').first()
        
        response_data = {
            'quotation': {
                'id': quotation.id,
                'original_amount': str(quotation.total_amount),
                'current_negotiated_amount': str(latest_negotiation.proposed_amount) if latest_negotiation else str(quotation.total_amount),
                'status': quotation.status,
                'vendor_name': quotation.vendor_name,
                'can_negotiate': quotation.status in ['sent', 'negotiating']
            },
            'negotiations': serializer.data,
            'total_negotiations': queryset.count(),
            'latest_negotiation': {
                'initiated_by': latest_negotiation.initiated_by,
                'proposed_amount': str(latest_negotiation.proposed_amount),
                'message': latest_negotiation.message,
                'created_at': latest_negotiation.created_at.isoformat()
            } if latest_negotiation else None,
            'next_negotiator': 'vendor' if latest_negotiation and latest_negotiation.initiated_by == 'customer' else 'customer' if latest_negotiation else None
        }
        
        return success_response(
            data=response_data,
            message=ResponseMessages.NEGOTIATIONS_FOUND.format(count=queryset.count()),
            status_code=status.HTTP_200_OK
        )


class AcceptNegotiationView(APIView, StandardizedResponseMixin):
    """Accept a negotiation and update quotation"""
    permission_classes = [IsCustomerOrVendor]
    
    def post(self, request, negotiation_id):
        try:
            negotiation = QuotationNegotiation.objects.get(id=negotiation_id)
            quotation = negotiation.quotation
            user = request.user
            
            # Check if user is authorized to accept this negotiation
            if user.role == 'customer' and user != quotation.quotation_request.customer:
                return error_response(
                    error="You can only accept negotiations for your own quotation requests",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            elif user.role == 'vendor' and user != quotation.vendor:
                return error_response(
                    error="You can only accept negotiations for your own quotations",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            # Check if the negotiation was initiated by the other party (prevent self-acceptance)
            if ((user.role == 'customer' and negotiation.initiated_by == 'customer') or
                (user.role == 'vendor' and negotiation.initiated_by == 'vendor')):
                return error_response(
                    error=ErrorMessages.CANNOT_ACCEPT_OWN_NEGOTIATION,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Prevent accepting negotiations for non-negotiating quotations
            if quotation.status not in ['sent', 'negotiating']:
                return error_response(
                    error=ErrorMessages.CANNOT_NEGOTIATE_STATUS.format(status=quotation.status),
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Use service layer for acceptance logic
            try:
                acceptance_result = QuotationStatusService.accept_negotiation(negotiation, user)
            except ValueError as e:
                return error_response(
                    error=str(e),
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Prepare comprehensive response data
            response_data = {
                'negotiation_accepted': {
                    'id': negotiation.id,
                    'initiated_by': negotiation.initiated_by,
                    'accepted_by': user.role,
                    'original_amount': str(acceptance_result['original_amount']),
                    'final_amount': str(acceptance_result['final_amount']),
                    'savings': str(acceptance_result['savings']),
                    'message': negotiation.message
                },
                'quotation': {
                    'id': quotation.id,
                    'vendor_name': quotation.vendor_name,
                    'status': quotation.status,
                    'total_negotiations': quotation.negotiations.count()
                },
                'quotation_request_id': quotation.quotation_request.id,
                'other_quotations_rejected': acceptance_result['rejected_count']
            }
            
            # Build acceptance message
            final_amount = acceptance_result['final_amount']
            original_amount = acceptance_result['original_amount']
            acceptance_message = ResponseMessages.NEGOTIATION_ACCEPTED.format(amount=final_amount)
            
            if original_amount != final_amount:
                savings = acceptance_result['savings']
                if savings > 0:
                    acceptance_message += f" (Saved ₹{savings})"
                else:
                    acceptance_message += f" (Additional ₹{abs(savings)})"
            
            return success_response(
                data=response_data,
                message=acceptance_message,
                status_code=status.HTTP_200_OK
            )
            
        except QuotationNegotiation.DoesNotExist:
            return error_response(
                error='Negotiation not found',
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return error_response(
                error=f'Failed to accept negotiation: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
