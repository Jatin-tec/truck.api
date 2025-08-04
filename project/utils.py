"""
Utility functions for the project
"""
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from typing import Any, Dict, List, Optional, Union


def create_standardized_response(
    success: bool,
    data: Optional[Any] = None,
    message: Optional[str] = None,
    error: Optional[str] = None,
    errors: Optional[Dict[str, List[str]]] = None,
    status_code: int = status.HTTP_200_OK
) -> Response:
    """
    Create a standardized API response format.
    
    Args:
        success: Boolean indicating if the request was successful
        data: Response data (optional)
        message: Success or info message (optional)
        error: Error message for failed requests (optional)
        errors: Field-specific validation errors (optional)
        status_code: HTTP status code
    
    Returns:
        Response object with standardized format
    """
    response_data = {"success": success}
    
    if data is not None:
        response_data["data"] = data
    
    if message:
        response_data["message"] = message
    
    if error:
        response_data["error"] = error
    
    if errors:
        response_data["errors"] = errors
    
    return Response(response_data, status=status_code)


def success_response(
    data: Optional[Any] = None,
    message: Optional[str] = None,
    status_code: int = status.HTTP_200_OK
) -> Response:
    """Create a successful response."""
    return create_standardized_response(
        success=True,
        data=data,
        message=message,
        status_code=status_code
    )


def error_response(
    error: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    errors: Optional[Dict[str, List[str]]] = None
) -> Response:
    """Create an error response."""
    return create_standardized_response(
        success=False,
        error=error,
        errors=errors,
        status_code=status_code
    )


def validation_error_response(
    errors: Dict[str, List[str]],
    status_code: int = status.HTTP_400_BAD_REQUEST
) -> Response:
    """Create a validation error response."""
    return create_standardized_response(
        success=False,
        error="Validation failed",
        errors=errors,
        status_code=status_code
    )


class StandardizedAPIView(APIView):
    """
    Base APIView class that provides standardized response methods.
    
    This class provides convenience methods for creating standardized responses
    and can be used as a base class for custom APIView implementations.
    """
    
    def success_response(
        self,
        data: Optional[Any] = None,
        message: Optional[str] = None,
        status_code: int = status.HTTP_200_OK
    ) -> Response:
        """Create a successful response."""
        return success_response(data=data, message=message, status_code=status_code)
    
    def error_response(
        self,
        error: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        errors: Optional[Dict[str, List[str]]] = None
    ) -> Response:
        """Create an error response."""
        return error_response(error=error, status_code=status_code, errors=errors)
    
    def validation_error_response(
        self,
        errors: Dict[str, List[str]],
        status_code: int = status.HTTP_400_BAD_REQUEST
    ) -> Response:
        """Create a validation error response."""
        return validation_error_response(errors=errors, status_code=status_code)


class StandardizedResponseMixin:
    """Mixin to standardize responses for DRF generic views."""
    
    def list(self, request, *args, **kwargs):
        """Override list to use standardized response format."""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_data = self.get_paginated_response(serializer.data).data
            return success_response(
                data=response_data,
                message=f"Retrieved {len(serializer.data)} items"
            )

        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message=f"Retrieved {len(serializer.data)} items"
        )

    def create(self, request, *args, **kwargs):
        """Override create to use standardized response format."""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        self.perform_create(serializer)
        return success_response(
            data=serializer.data,
            message="Created successfully",
            status_code=status.HTTP_201_CREATED
        )

    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to use standardized response format."""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return success_response(
                data=serializer.data,
                message="Retrieved successfully"
            )
        except Exception as e:
            return error_response(str(e), status.HTTP_404_NOT_FOUND)

    def update(self, request, *args, **kwargs):
        """Override update to use standardized response format."""
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)
            
            self.perform_update(serializer)
            return success_response(
                data=serializer.data,
                message="Updated successfully"
            )
        except Exception as e:
            return error_response(str(e), status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """Override destroy to use standardized response format."""
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return success_response(
                message="Deleted successfully",
                status_code=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            return error_response(str(e), status.HTTP_400_BAD_REQUEST)
