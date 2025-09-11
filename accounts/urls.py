from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserRegistrationView,
    UserLoginView,
    UserLogoutView,
    UserProfileView,
    UpdateUserProfileView,
    user_info,
    CustomTokenObtainPairView,
    AdminUserListView,
    AdminUserDetailView,
    change_user_role
)

app_name = 'accounts'

urlpatterns = [
    # Authentication endpoints
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    
    # User profile endpoints
    path('me/', user_info, name='user_info'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('profile/update/', UpdateUserProfileView.as_view(), name='update_profile'),
    
    # Admin endpoints for user management (ADM-01)
    path('admin/users/', AdminUserListView.as_view(), name='admin_user_list'),
    path('admin/users/<int:pk>/', AdminUserDetailView.as_view(), name='admin_user_detail'),
    path('admin/users/<int:user_id>/change-role/', change_user_role, name='change_user_role'),
]