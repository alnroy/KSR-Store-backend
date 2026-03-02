from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Category, Product, Order, OrderItem, Review, SavedAddress
import json

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=True) # Enforce email existence

    class Meta:
        model = User
        fields = ('username', 'password', 'email')

    def validate_email(self, value):
        # Prevent multiple accounts from using the same email
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def create(self, validated_data):
        # CRITICAL FIX: User is created as INACTIVE. 
        # They cannot log in until they verify the OTP.
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            is_active=False 
        )
        return user
    
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Review
        fields = ['id', 'user', 'user_name', 'product', 'rating', 'comment', 'created_at']
        read_only_fields = ['user'] # The backend will automatically set the user based on their login token

# 2. Update the ProductSerializer to include the new reviews data
class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    
    # NEW: Fetch all related reviews and calculate the average
    reviews = ReviewSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Product
        # NEW: Add 'reviews' and 'average_rating' to the fields list
        fields = [
            'id', 'name', 'description', 'price', 'offer_price', 'is_combo', 
            'image', 'stock', 'category', 'category_name', 'reviews', 'average_rating']

    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if reviews:
            # Calculates the math: (Sum of all ratings) / (Total number of reviews)
            return round(sum(r.rating for r in reviews) / len(reviews), 1)
        return 0

# ==========================================
# NEW: OTP SERIALIZERS
# ==========================================

class VerifyOTPSerializer(serializers.Serializer):
    """Used when the user enters the OTP to activate their account."""
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

class PasswordResetRequestSerializer(serializers.Serializer):
    """Used when the user asks for a password reset email."""
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    """Used when the user submits the OTP and their new password."""
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)
    
class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    # NEW: Tell Django to grab the image from the linked product
    product_image = serializers.ImageField(source='product.image', read_only=True)
    
    # NEW: We should also grab the description and category for your modal
    product_description = serializers.ReadOnlyField(source='product.description')
    product_category = serializers.ReadOnlyField(source='product.category.name')

    class Meta:
        model = OrderItem
        # ADD the new fields to the array
        fields = ['product', 'product_name', 'product_image', 'product_description', 'product_category', 'quantity', 'price']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True) 

    class Meta:
        model = Order
        # ADDED: 'rejection_reason'
        fields = ['id', 'full_name', 'email', 'address', 'total_amount', 'payment_screenshot', 'status', 'rejection_reason', 'items', 'created_at']
        read_only_fields = ['id', 'created_at'] 
        # FIXED: Removed 'status' so the Admin can actually update it!
        read_only_fields = ['id', 'created_at']
    def to_internal_value(self, data):
        # Check if 'items' is coming in as a string (which happens with FormData)
        items_data = data.get('items')
        if isinstance(items_data, str):
            try:
                # We create a mutable copy of the data to fix it
                mutable_data = data.copy()
                mutable_data['items'] = json.loads(items_data)
                return super().to_internal_value(mutable_data)
            except json.JSONDecodeError:
                pass
        
        return super().to_internal_value(data)
    # -------------------------------

    def create(self, validated_data):
        # 1. Pop the items array out
        items_data = validated_data.pop('items')
        
        # 2. Create the Order
        # The 'user' is ALREADY inside validated_data if they are logged in!
        order = Order.objects.create(**validated_data)

        # 3. Create OrderItems & Deduct Stock
        for item_data in items_data:
            product = item_data['product']
            quantity = item_data['quantity']
            
            OrderItem.objects.create(order=order, **item_data)
            
            # Update physical stock
            product.stock -= quantity
            product.save()
            
        return order
    
class SavedAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedAddress
        fields = ['id', 'full_name', 'email', 'address']