from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, UserProfile


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration (CUS-01)
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 
            'password', 'password_confirm', 'phone_number', 
            'date_of_birth', 'driver_license_number', 'role'
        ]
        extra_kwargs = {
            'role': {'default': 'customer'}
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        
        # Remove password_confirm from attrs
        attrs.pop('password_confirm', None)
        return attrs
    
    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return value.lower()
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        # Create user profile
        UserProfile.objects.create(user=user)
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login (CUS-01)
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(username=email, password=password)
            
            if not user:
                raise serializers.ValidationError('Invalid credentials.')
            
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include email and password.')


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user data
    """
    full_name = serializers.ReadOnlyField()
    profile = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'full_name', 'phone_number', 'role', 'date_of_birth', 
            'driver_license_number', 'is_verified', 'created_at', 'profile'
        ]
        read_only_fields = ['id', 'created_at', 'is_verified', 'role']
    
    def get_profile(self, obj):
        try:
            profile = obj.profile
            return {
                'address': profile.address,
                'city': profile.city,
                'country': profile.country,
                'emergency_contact_name': profile.emergency_contact_name,
                'emergency_contact_phone': profile.emergency_contact_phone,
                'profile_picture': profile.profile_picture.url if profile.profile_picture else None
            }
        except UserProfile.DoesNotExist:
            return None


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile
    """
    class Meta:
        model = UserProfile
        fields = [
            'address', 'city', 'country', 'emergency_contact_name',
            'emergency_contact_phone', 'profile_picture'
        ]


class TokenSerializer(serializers.Serializer):
    """
    Serializer for JWT tokens
    """
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer(read_only=True)


def get_tokens_for_user(user):
    """
    Generate JWT tokens for a user
    """
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': UserSerializer(user).data
    }