from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserProfileView
from . import views  # <--- ADD THIS LINE
# Import all the ViewSets and the new Auth Views
from .views import (
    BrandViewSet,
    ProductViewSet, 
    OrderViewSet, 
    CategoryViewSet,
    RegisterView,
    VerifyOTPView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    create_review,
    delete_review,
    SavedAddressViewSet,
    ShoppableVideoViewSet,
    AttributeViewSet
)

# 1. Router for Data Models
router = DefaultRouter()
router.register(r'brands', BrandViewSet, basename='brand')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'addresses', SavedAddressViewSet, basename='address')
router.register(r'videos', ShoppableVideoViewSet, basename='video')
router.register(r'attributes', AttributeViewSet, basename='attribute')

# 2. URL Patterns
urlpatterns = [
    # Include the router URLs
    path('', include(router.urls)),
    
    # 2. NEW: Review Endpoints
    path('products/<int:pk>/review/', create_review, name='create-review'),
    path('reviews/<int:pk>/', delete_review, name='delete-review'),
    
    # Custom Authentication & OTP URLs
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/me/', UserProfileView.as_view(), name='user-profile'),
    path('auth/verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('auth/password-reset-request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('auth/password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]