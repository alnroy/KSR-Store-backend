from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Category, Product, Order, OrderItem, Review, SavedAddress, ProductVariant, ProductAttribute, ProductImage
import json

# ==========================================
# 1. ATTRIBUTE & VARIANT SERIALIZERS
# ==========================================

class ProductAttributeSerializer(serializers.ModelSerializer):
    """NEW: This fixes your 404 error in the Admin Dashboard"""
    class Meta:
        model = ProductAttribute
        fields = ['id', 'name']

class ProductVariantSerializer(serializers.ModelSerializer):
    attribute_name = serializers.ReadOnlyField(source='attribute.name')

    class Meta:
        model = ProductVariant
        fields = ['id', 'attribute', 'attribute_name', 'value', 'price_modifier', 'stock']

# ==========================================
# 2. AUTH & USER SERIALIZERS
# ==========================================

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'email')

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            is_active=False 
        )
        return user

class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)

# ==========================================
# 3. SHOP CORE SERIALIZERS
# ==========================================

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image']

class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Review
        fields = ['id', 'user', 'user_name', 'product', 'rating', 'comment', 'created_at']
        read_only_fields = ['user']

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    variants = ProductVariantSerializer(many=True, read_only=True) 
    reviews = ReviewSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'offer_price', 'is_combo', 
            'image', 'images', 'stock', 'category', 'category_name', 'reviews', 'average_rating', 'variants','is_hero_marquee',
        ]

    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if reviews:
            return round(sum(r.rating for r in reviews) / len(reviews), 1)
        return 0

    def create(self, validated_data):
        request = self.context.get('request')
        variants_raw = request.data.get('variants_data') # Stringified JSON from Admin Dashboard
        
        product = Product.objects.create(**validated_data)

        # Handle multiple images
        if request and request.FILES:
            uploaded_images = request.FILES.getlist('uploaded_images')
            for img in uploaded_images:
                ProductImage.objects.create(product=product, image=img)

        if variants_raw:
            try:
                variants_list = json.loads(variants_raw)
                for var in variants_list:
                    ProductVariant.objects.create(
                        product=product,
                        attribute_id=var['attribute'],
                        value=var['value'],
                        price_modifier=var['price_modifier'],
                        stock=var['stock']
                    )
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        return product

    def update(self, instance, validated_data):
        request = self.context.get('request')
        variants_raw = request.data.get('variants_data')

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Handle multiple images on update
        if request and request.FILES:
            uploaded_images = request.FILES.getlist('uploaded_images')
            for img in uploaded_images:
                ProductImage.objects.create(product=instance, image=img)

        if variants_raw:
            try:
                variants_list = json.loads(variants_raw)
                instance.variants.all().delete() # Simple overwrite strategy
                for var in variants_list:
                    ProductVariant.objects.create(
                        product=instance,
                        attribute_id=var['attribute'],
                        value=var['value'],
                        price_modifier=var['price_modifier'],
                        stock=var['stock']
                    )
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        return instance

# ==========================================
# 4. ORDER SERIALIZERS
# ==========================================

class OrderItemSerializer(serializers.ModelSerializer):
    # Use stored snapshot first; only fall back to live product.name if snapshot is empty
    product_name = serializers.SerializerMethodField()
    product_image = serializers.ImageField(source='product.image', read_only=True)
    product_description = serializers.ReadOnlyField(source='product.description')
    product_category = serializers.ReadOnlyField(source='product.category.name')

    def get_product_name(self, obj):
        # Use snapshotted name first (survives product deletion)
        return obj.product_name or (obj.product.name if obj.product else 'Deleted Product')

    class Meta:
        model = OrderItem
        fields = ['product', 'product_name', 'product_image', 'product_description',
                  'product_category', 'quantity', 'price', 'selected_options']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True) 

    class Meta:
        model = Order
        fields = ['id', 'full_name', 'email', 'address', 'total_amount', 
                  'payment_screenshot', 'status', 'rejection_reason', 'items', 'created_at']
        read_only_fields = ['id', 'created_at']

    def to_internal_value(self, data):
        items_data = data.get('items')
        if isinstance(items_data, str):
            try:
                mutable_data = data.copy()
                mutable_data['items'] = json.loads(items_data)
                return super().to_internal_value(mutable_data)
            except json.JSONDecodeError:
                pass
        return super().to_internal_value(data)

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)

        for item_data in items_data:
            product = item_data.get('product')
            quantity = item_data.get('quantity', 1)

            # Snapshot the product name at purchase time
            if product:
                item_data['product_name'] = product.name

            OrderItem.objects.create(order=order, **item_data)

            # Update stock; delete product if it runs out
            if product:
                product.stock -= quantity
                if product.stock <= 0:
                    product.delete()
                else:
                    product.save()

        return order

class SavedAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedAddress
        fields = ['id', 'full_name', 'email', 'address']