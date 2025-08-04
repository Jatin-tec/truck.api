from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.authtoken.models import Token
from authentication.api.serializers import LoginSerializer, SendOTPSerializer, VerifyOTPSerializer
from rest_framework.views import APIView
from rest_framework import status
from authentication.models import CustomUser
from django.http import JsonResponse
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django_ratelimit.decorators import ratelimit
from project.utils import success_response, StandardizedAPIView
from rest_framework.decorators import api_view
from rest_framework.authtoken.models import Token
from authentication.api.serializers import LoginSerializer, SendOTPSerializer, VerifyOTPSerializer
from rest_framework.views import APIView
from rest_framework import status
from authentication.models import CustomUser
from django.http import JsonResponse
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator
from rest_framework_simplejwt.tokens import RefreshToken
from django_ratelimit.decorators import ratelimit
from project.utils import success_response, StandardizedAPIView


@api_view(['GET'])
def getRoutes(request):
    routes = [
        '/api/token/',
        '/api/token/refresh/',
        '/api/token/verify/',

        '/api/auth/register/',
        '/api/auth/login/',
        '/api/auth/logout/',
        
        '/api/auth/users/',
        '/api/auth/user/<str:pk>/',
        '/api/auth/user/<str:pk>/update/',
        '/api/auth/user/<str:pk>/delete/',
        ]    
    return success_response(data=routes, message="Available authentication routes")


class LoginView(StandardizedAPIView):
    permission_classes = []
    def post(self, request, *args, **kwargs):
        try:
            serializer = LoginSerializer(data=request.data)
            if not serializer.is_valid():
                return self.validation_error_response(serializer.errors)
            
            validated_data = serializer.validated_data
            user = CustomUser.objects.get(email=validated_data['email'])

            return self.success_response(
                data={
                    'user': {
                        'email': user.email,
                        'role': user.role,
                        'phone_number': user.phone_number,
                    },
                    'tokens': validated_data['tokens']
                },
                message="Login successful"
                
            )
        except CustomUser.DoesNotExist:
            return self.error_response("Invalid credentials", status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return self.error_response(str(e), status.HTTP_400_BAD_REQUEST)
    

class ValidateToken(StandardizedAPIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return self.error_response("Authorization header missing or invalid", status.HTTP_400_BAD_REQUEST)
            
            token = auth_header.split(' ')[1]
            if not token:
                return self.error_response("Token is required", status.HTTP_400_BAD_REQUEST)
            
            try:
                user = Token.objects.get(key=token).user
                return self.success_response(
                    data={
                        "valid": True,
                        "user_id": user.pk,
                        "role": user.role
                    },
                    message="Token is valid"
                )
            except Token.DoesNotExist:
                return self.success_response(
                    data={"valid": False},
                    message="Token is invalid"
                )
        except Exception as e:
            return self.error_response(str(e), status.HTTP_400_BAD_REQUEST)    


class SendOTPView(StandardizedAPIView):
    permission_classes = []

    @method_decorator(ratelimit(key='ip', rate='3/h', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        try:
            print('send otp', request.data)
            serializer = SendOTPSerializer(data=request.data)
            if not serializer.is_valid():
                return self.validation_error_response(serializer.errors)
            
            serializer.send_otp()
            return self.success_response(message="OTP sent successfully")
        except Exception as e:
            return self.error_response(str(e), status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(StandardizedAPIView):
    permission_classes = []

    def post(self, request, *args, **kwargs):
        try:
            serializer = VerifyOTPSerializer(data=request.data)
            if not serializer.is_valid():
                return self.validation_error_response(serializer.errors)
            
            user = CustomUser.objects.get(phone_number=serializer.validated_data['phone_number'])
            tokens = serializer.create_tokens()

            return self.success_response(
                data={
                    'user': {
                        'email': user.email,
                        'name': user.name,
                        'role': user.role,
                        'phone_number': user.phone_number,
                    },
                    'tokens': tokens
                },
                message="OTP verified successfully"
            )
        except CustomUser.DoesNotExist:
            return self.error_response("User not found", status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return self.error_response(str(e), status.HTTP_400_BAD_REQUEST)


class UpdateUserView(StandardizedAPIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        try:
            user = request.user
            user_data = request.data
            user.name = user_data.get('name', user.name)
            user.email = user_data.get('email', user.email)
            user.phone_number = user_data.get('phone_number', user.phone_number)
            user.save()

            refresh = RefreshToken.for_user(user)

            return self.success_response(
                data={
                    'user': {
                        'email': user_data.get('email', user.email),
                        'name': user_data.get('name', user.name),
                        'role': user.role,
                        'phone_number': user.phone_number,
                    },
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }
                },
                message="User updated successfully"
            )
        except Exception as e:
            return self.error_response(str(e), status.HTTP_400_BAD_REQUEST)
        
class GetUserView(StandardizedAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            return self.success_response(
                data={
                    'user': {
                        'email': user.email,
                        'phone_number': user.phone_number,
                        'name': user.name,
                        'age': user.age,
                    }
                },
                message="User data retrieved successfully"
            )
        except Exception as e:
            return self.error_response(str(e), status.HTTP_400_BAD_REQUEST)


class TokenRefreshView(StandardizedAPIView):
    """
    Custom token refresh view that returns standardized response format
    """
    permission_classes = []
    
    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get('refresh')
            
            if not refresh_token:
                return self.error_response(
                    "Refresh token is required", 
                    status.HTTP_400_BAD_REQUEST
                )
            
            try:
                # Validate and refresh the token
                refresh = RefreshToken(refresh_token)
                
                # Get new access token
                access_token = str(refresh.access_token)
                
                # Since ROTATE_REFRESH_TOKENS is True, we need to get a new refresh token
                # by creating a fresh RefreshToken instance
                user_id = refresh.payload.get('user_id')
                if user_id:
                    user = CustomUser.objects.get(id=user_id)
                    new_refresh = RefreshToken.for_user(user)
                    
                    return self.success_response(
                        data={
                            'access': str(new_refresh.access_token),
                            'refresh': str(new_refresh)
                        },
                        message="Token refreshed successfully"
                    )
                else:
                    return self.error_response(
                        "Invalid token payload", 
                        status.HTTP_401_UNAUTHORIZED
                    )
                
            except TokenError as e:
                return self.error_response(
                    "Invalid refresh token", 
                    status.HTTP_401_UNAUTHORIZED
                )
                
        except CustomUser.DoesNotExist:
            return self.error_response(
                "User not found", 
                status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            return self.error_response(str(e), status.HTTP_400_BAD_REQUEST)