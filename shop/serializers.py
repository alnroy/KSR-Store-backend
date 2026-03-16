from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Brand, Category, Product, Order, OrderItem, Review, SavedAddress, ProductVariant, ProductAttribute, ProductImage, ShoppableVideo
import json

# ==========================================
# 0. BRAND SERIALIZER
# ==========================================

class BrandSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None

    class Meta:
        model = Brand
        fields = ['id', 'name', 'logo', 'logo_url']

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

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError("Password must contain at least one digit.")
        if not any(char.isupper() for char in value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter.")
        if not any(char.islower() for char in value):
            raise serializers.ValidationError("Password must contain at least one lowercase letter.")
        return value

    def validate_username(self, value):
        import re
        if not re.match(r'^[\w.@+-]+$', value):
            raise serializers.ValidationError("Username can only contain letters, numbers, and @/./+/-/_ characters.")
        return value

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

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate_comment(self, value):
        if len(value) > 500:
            raise serializers.ValidationError("Comment cannot exceed 500 characters.")
        return value

class ShoppableVideoSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    product_price = serializers.ReadOnlyField(source='product.price')
    product_offer_price = serializers.ReadOnlyField(source='product.offer_price')
    product_image = serializers.SerializerMethodField()

    def get_product_image(self, obj):
        if obj.product.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.product.image.url)
            return obj.product.image.url
        return None

    class Meta:
        model = ShoppableVideo
        fields = ['id', 'title', 'video_file', 'product', 'product_name', 'product_price', 'product_offer_price', 'product_image', 'created_at']

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    brand_name = serializers.ReadOnlyField(source='brand.name')
    variants = ProductVariantSerializer(many=True, read_only=True) 
    reviews = ReviewSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    shoppable_videos = ShoppableVideoSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'offer_price', 'is_combo', 
            'image', 'images', 'stock', 'category', 'category_name', 'brand', 'brand_name', 
            'reviews', 'average_rating', 'variants','is_hero_marquee', 'shoppable_videos', 'created_at'
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
                    price_mod = var.get('price_modifier')
                    if price_mod == "" or price_mod is None:
                        price_mod = 0
                    
                    ProductVariant.objects.create(
                        product=product,
                        attribute_id=var['attribute'],
                        value=var['value'],
                        price_modifier=price_mod,
                        stock=var.get('stock', 0)
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
                    price_mod = var.get('price_modifier')
                    if price_mod == "" or price_mod is None:
                        price_mod = 0
                        
                    ProductVariant.objects.create(
                        product=instance,
                        attribute_id=var['attribute'],
                        value=var['value'],
                        price_modifier=price_mod,
                        stock=var.get('stock', 0)
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
    product_image = serializers.ImageField(source='product.image', read_only=True, allow_null=True)
    product_description = serializers.SerializerMethodField()
    product_category = serializers.SerializerMethodField()

    def get_product_name(self, obj):
        # Use snapshotted name first (survives product deletion)
        return obj.product_name or (obj.product.name if obj.product else 'Deleted Product')

    def get_product_description(self, obj):
        return obj.product.description if obj.product else "Description not available"

    def get_product_category(self, obj):
        return obj.product.category.name if obj.product and obj.product.category else "Other"

    class Meta:
        model = OrderItem
        fields = ['product', 'product_name', 'product_image', 'product_description',
                  'product_category', 'quantity', 'price', 'selected_options']
        # Price should be calculated by backend, but we need it for validation or initial data
        # Actually, let's keep it but override it in OrderSerializer.create for security

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True) 

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'full_name', 'email', 'total_amount', 'transaction_id', 'payment_screenshot', 
            'status', 'rejection_reason', 'items', 'created_at',
            'mobile_number', 'country_region', 'house_info', 'street_info',
            'landmark', 'pincode', 'city', 'state', 'address'
        ]
        read_only_fields = ['id', 'user', 'created_at']

    def validate_mobile_number(self, value):
        import re
        # Basic validation for 10-15 digit mobile numbers
        if not re.match(r'^\+?1?\d{9,15}$', value):
            raise serializers.ValidationError("Please enter a valid mobile number (10-15 digits).")
        return value

    def validate_pincode(self, value):
        import re
        # Validation for 6-digit Indian pincode (or adjust for international)
        if not re.match(r'^\d{6}$', value):
            raise serializers.ValidationError("Please enter a valid 6-digit pincode.")
        return value

    def to_internal_value(self, data):
        # 1. Handle QueryDict conversion to support complex nested objects and stringified JSON
        if hasattr(data, 'dict'):
            new_data = data.dict()
            # items might be multiple in a QueryDict if not stringified, but here it's stringified
            if 'items' in new_data and isinstance(new_data['items'], str):
                try:
                    new_data['items'] = json.loads(new_data['items'])
                except json.JSONDecodeError:
                    pass
        else:
            new_data = data.copy() if hasattr(data, 'copy') else dict(data)
            if 'items' in new_data and isinstance(new_data['items'], str):
                try:
                    new_data['items'] = json.loads(new_data['items'])
                except json.JSONDecodeError:
                    pass
        
        # 2. Ensure total_amount is not an empty string
        if 'total_amount' in new_data and new_data['total_amount'] == '':
            new_data['total_amount'] = '0.00'

        return super().to_internal_value(new_data)

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        
        # Security check: Recalculate total_amount on backend instead of trusting frontend
        calculated_total = 0
        
        # Create the order first (we can update total later if mismatch)
        order = Order.objects.create(**validated_data)

        for item_data in items_data:
            product = item_data.get('product')
            quantity = item_data.get('quantity', 1)
            
            if product:
                # Security: Force correct price from database
                actual_price = product.offer_price if product.offer_price else product.price
                item_data['price'] = actual_price
                item_data['product_name'] = product.name
                
                # Increment running total
                calculated_total += actual_price * quantity

                # Deduct stock
                product.stock -= quantity
                if product.stock < 0:
                    product.stock = 0
                product.save()

            OrderItem.objects.create(order=order, **item_data)

        # Update order with correctly calculated total
        order.total_amount = calculated_total
        order.save()

        return order

class SavedAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedAddress
        fields = [
            'id', 'full_name', 'email', 'mobile_number', 'country_region',
            'house_info', 'street_info', 'landmark', 'pincode', 'city',
            'state', 'is_default', 'address', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']