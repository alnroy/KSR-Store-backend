from rest_framework import viewsets, filters, generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth.models import User
from .models import Category, Product, Order, Review, OrderItem, SavedAddress
from .serializers import (
    CategorySerializer, 
    ProductSerializer, 
    OrderSerializer, 
    RegisterSerializer,
    SavedAddressSerializer,
    ProductAttribute
)
import random
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import status, views
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import OTPRecord
from .serializers import (
    VerifyOTPSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer
)
from rest_framework.decorators import api_view, permission_classes
from .serializers import ReviewSerializer
# shop/views.py
from rest_framework import viewsets, filters, generics, views, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .permissions import IsAdminUserOrReadOnly 
import json
from .serializers import ProductAttributeSerializer

class RegisterView(generics.CreateAPIView):
    """Handles User Registration and sends the initial OTP."""
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 1. Create the user (is_active=False based on our serializer logic)
        user = serializer.save()

        # 2. Generate, save, and send OTP
        otp = generate_otp()
        OTPRecord.objects.create(user=user, otp=otp)
        send_otp_email(user.email, otp)

        return Response({
            "message": "Registration successful! A 6-digit OTP has been sent to your email. Please verify to activate your account."
        }, status=status.HTTP_201_CREATED)

class AttributeListView(generics.ListAPIView):
    queryset = ProductAttribute.objects.all()
    serializer_class = ProductAttributeSerializer
    # Optional: permission_classes = [IsAdminUser]

class CategoryViewSet(viewsets.ModelViewSet): # Upgraded from ReadOnlyModelViewSet
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUserOrReadOnly] # 2. Applied Security Rule

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminUserOrReadOnly]  # Read is public, write/delete is admin-only
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['name', 'description', 'brand_name']
    filterset_fields = ['category', 'category__name']

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Order.objects.none()
        if self.request.user.is_staff:
            return Order.objects.all().order_by('-created_at')
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

    def get_permissions(self):
        
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        # 1. Manually pull the data from request.data
        data = request.data
        items_json = data.get('items')

        # 2. VALIDATION: Ensure items exist and parse them
        if not items_json:
            return Response({"error": "No items found in your cart."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            items_data = json.loads(items_json)
        except Exception:
            return Response({"error": "Invalid format for items."}, status=status.HTTP_400_BAD_REQUEST)

        # 3. STOCK CHECK (The logic we built earlier)
        for item in items_data:
            product = Product.objects.get(id=item['product'])
            if product.stock < item['quantity']:
                return Response({"error": f"Out of stock: {product.name}"}, status=status.HTTP_400_BAD_REQUEST)

        # 4. SAVE THE ORDER (Minus the items for now)
        order = Order.objects.create(
            user=request.user,
            full_name=data.get('full_name'),
            email=data.get('email'),
            address=data.get('address'),
            total_amount=data.get('total_amount'),
            payment_screenshot=data.get('payment_screenshot')
        )

        # 5. CREATE ORDER ITEMS & DEDUCT STOCK
        for item in items_data:
            product = Product.objects.get(id=item['product'])
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item['quantity'],
                price=item['price']
            )
            # Deduct stock
            product.stock -= item['quantity']
            product.save()

        return Response({"message": "Order placed successfully!", "id": order.id}, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != 'PENDING':
            return Response(
                {"error": "Paid orders cannot be cancelled."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # SECURITY SECURE: Block users from editing if not PENDING (Admins bypass this)
        if instance.status != 'PENDING' and not request.user.is_staff:
            return Response(
                {"error": "This order is already being processed. You can no longer change the address."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Ensure they can ONLY patch the address (prevent them from changing the total_amount!)
        if not request.user.is_staff:
            allowed_keys = ['address']
            # If they try to send anything other than 'address', reject it
            if any(key not in allowed_keys for key in request.data.keys()):
                 return Response({"error": "You are only allowed to update your shipping address."}, status=status.HTTP_400_BAD_REQUEST)

        return super().update(request, *args, **kwargs)
    
# --- Helper Functions ---
def generate_otp():
    """Generates a secure 6-digit OTP."""
    return str(random.randint(100000, 999999))

def send_otp_email(email, otp, is_reset=False):
    """Sends the OTP to the user. (Currently configured to print to your terminal)."""
    subject = 'ProFish Gear: Password Reset OTP' if is_reset else 'ProFish Gear: Verify your Account'
    message = f'Your 6-digit OTP is: {otp}\n\nThis code will expire in 10 minutes.'
    # Ensure DEFAULT_FROM_EMAIL is set in settings.py
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@profishgear.com')
    send_mail(subject, message, from_email, [email], fail_silently=False)

class VerifyOTPView(views.APIView):
    """Verifies the OTP and activates the account."""
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']

        try:
            user = User.objects.get(email=email)
            # Get the most recent unused OTP for this user
            otp_record = OTPRecord.objects.filter(user=user, otp=otp, is_used=False).latest('created_at')
            
            if not otp_record.is_valid():
                return Response({"error": "OTP has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)
            
            # 3. Activate User & Mark OTP as used
            user.is_active = True
            user.save()
            otp_record.is_used = True
            otp_record.save()

            # 4. Professional Touch: Auto-Login by issuing JWT tokens immediately
            refresh = RefreshToken.for_user(user)
            return Response({
                "message": "Account activated successfully.",
                "access": str(refresh.access_token),
                "refresh": str(refresh)
            }, status=status.HTTP_200_OK)

        except (User.DoesNotExist, OTPRecord.DoesNotExist):
            return Response({"error": "Invalid email or OTP."}, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(views.APIView):
    """Initiates the password reset process."""
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)
            otp = generate_otp()
            OTPRecord.objects.create(user=user, otp=otp)
            send_otp_email(user.email, otp, is_reset=True)
        except User.DoesNotExist:
            # Security Best Practice: Never reveal if an email exists in the system to prevent enumeration.
            pass 

        return Response({
            "message": "If that email exists in our system, an OTP has been sent."
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(views.APIView):
    """Verifies the OTP and sets the new password."""
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']

        try:
            user = User.objects.get(email=email)
            otp_record = OTPRecord.objects.filter(user=user, otp=otp, is_used=False).latest('created_at')

            if not otp_record.is_valid():
                return Response({"error": "OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)

            # --- X-RAY DEBUGGING: Watch your terminal! ---
            print("=========================================")
            print(f"🛠️ RESETTING PASSWORD FOR USERNAME: {user.username}")
            print(f"📧 LINKED EMAIL: {user.email}")
            print(f"🔑 EXACT NEW PASSWORD RECEIVED: '{new_password}'")
            print("=========================================")

            # Apply the new password and FORCE a save
            user.set_password(new_password)
            user.save()
            
            # Double check the save worked
            user.refresh_from_db()

            # Mark OTP as used
            otp_record.is_used = True
            otp_record.save()

            return Response({"message": "Password reset successfully. You can now log in."}, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            print(f"❌ ERROR: No user found with email {email}")
            return Response({"error": "Invalid email."}, status=status.HTTP_400_BAD_REQUEST)
        except OTPRecord.DoesNotExist:
            print("❌ ERROR: Invalid OTP.")
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)
                
# Add this to the bottom of shop/views.py
class UserProfileView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "id": request.user.id,
            "username": request.user.username,
            "email": request.user.email,
            "is_staff": request.user.is_staff # <-- This is the magic key
        })
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_review(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # ==========================================
    # 1. NEW SECURITY: Verified Purchase Check
    # ==========================================
    has_purchased = OrderItem.objects.filter(
        product=product,
        order__user=request.user,
        order__status__in=['PAID', 'SHIPPED'] # Only allow if the order is actually completed
    ).exists()

    if not has_purchased:
        return Response(
            {'error': 'Verified Buyers Only: You must purchase and pay for this item before leaving a review.'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # ==========================================
    # 2. SECURITY: Duplicate Review Check
    # ==========================================
    if Review.objects.filter(product=product, user=request.user).exists():
        return Response({'error': 'You have already reviewed this product.'}, status=status.HTTP_400_BAD_REQUEST)
    
    # ==========================================
    # 3. Save the Review
    # ==========================================
    serializer = ReviewSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user, product=product)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SavedAddressViewSet(viewsets.ModelViewSet):
    serializer_class = SavedAddressSerializer
    permission_classes = [IsAuthenticated] # Strictly for logged-in users

    def get_queryset(self):
        # Only return addresses belonging to this specific user
        return SavedAddress.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        # Automatically attach the logged-in user to the new address
        serializer.save(user=self.request.user)