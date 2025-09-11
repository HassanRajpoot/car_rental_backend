from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import get_user_model
from .models import User, UserProfile
from .serializers import (
    UserRegistrationSerializer, 
    UserLoginSerializer,
    UserSerializer,
    UserProfileSerializer,
    get_tokens_for_user
)

User = get_user_model()


class UserRegistrationView(generics.CreateAPIView):
    """
    User registration endpoint (CUS-01)
    POST /api/auth/register/
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens
        tokens = get_tokens_for_user(user)
        
        return Response({
            'success': True,
            'message': 'User registered successfully',
            'data': tokens
        }, status=status.HTTP_201_CREATED)


class UserLoginView(generics.GenericAPIView):
    """
    User login endpoint (CUS-01)
    POST /api/auth/login/
    """
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        tokens = get_tokens_for_user(user)
        
        return Response({
            'success': True,
            'message': 'Login successful',
            'data': tokens
        }, status=status.HTTP_200_OK)


class UserLogoutView(generics.GenericAPIView):
    """
    User logout endpoint (CUS-01)
    POST /api/auth/logout/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response({
                'success': True,
                'message': 'Logout successful'
            }, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    User profile endpoint
    GET/PUT /api/auth/profile/
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class UpdateUserProfileView(generics.UpdateAPIView):
    """
    Update user profile details
    PUT/PATCH /api/auth/profile/update/
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info(request):
    """
    Get current user information
    GET /api/auth/me/
    """
    serializer = UserSerializer(request.user)
    return Response({
        'success': True,
        'data': serializer.data
    })


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT token obtain view with additional user data
    """
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Get user data
            email = request.data.get('email') or request.data.get('username')
            try:
                user = User.objects.get(email=email)
                user_serializer = UserSerializer(user)
                response.data['user'] = user_serializer.data
                response.data['success'] = True
                response.data['message'] = 'Login successful'
            except User.DoesNotExist:
                pass
        
        return response


# Admin views for user management (ADM-01)
class AdminUserListView(generics.ListAPIView):
    """
    Admin view to list all users (ADM-01)
    GET /api/admin/users/
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Only allow admin users to access this view
        if not self.request.user.is_admin_user:
            return User.objects.none()
        
        role = self.request.query_params.get('role', None)
        if role:
            return User.objects.filter(role=role)
        return User.objects.all()


class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Admin view to manage individual users (ADM-01)
    GET/PUT/DELETE /api/admin/users/<id>/
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Only allow admin users to access this view
        if not self.request.user.is_admin_user:
            return User.objects.none()
        return User.objects.all()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_user_role(request, user_id):
    """
    Admin endpoint to change user roles (ADM-01)
    POST /api/admin/users/<user_id>/change-role/
    """
    if not request.user.is_admin_user:
        return Response({
            'success': False,
            'message': 'Permission denied'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = User.objects.get(id=user_id)
        new_role = request.data.get('role')
        
        if new_role not in ['customer', 'fleet_manager', 'admin']:
            return Response({
                'success': False,
                'message': 'Invalid role'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.role = new_role
        user.save()
        
        return Response({
            'success': True,
            'message': f'User role changed to {new_role}',
            'data': UserSerializer(user).data
        })
        
    except User.DoesNotExist:
        return Response({
            'success': False,
            'message': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)