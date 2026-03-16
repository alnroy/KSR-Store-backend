from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone

class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    logo = models.FileField(upload_to='brands/', blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Product(models.Model):
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    name = models.CharField("Product Name", max_length=200)
    description = models.TextField()
    
    # --- PRICING & OFFERS ---
    price = models.DecimalField("Original Price (₹)", max_digits=10, decimal_places=2)
    # Optional field: If left blank, there is no offer.
    offer_price = models.DecimalField("Offer Price (₹)", max_digits=10, decimal_places=2, blank=True, null=True)
    
    image = models.ImageField(upload_to='products/')
    stock = models.PositiveIntegerField(default=0)
    is_hero_marquee = models.BooleanField(default=False)
    # --- COMBOS ---
    # A simple switch. If True, it shows up on your special "Combos" page.
    is_combo = models.BooleanField("Is this a Combo Package?", default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    brand = models.ForeignKey(Brand, related_name='products', on_delete=models.SET_NULL, null=True, blank=True)
    specifications = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/gallery/')
    
    def __str__(self):
        return f"Image for {self.product.name}"

class Order(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    STATUS_CHOICES = [
        ('PENDING', 'Pending Payment'),
        ('VERIFYING', 'Verifying'),
        ('PAID', 'Paid'),
        ('FAILED','failed'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CLOSED', 'Closed'),
    ]

    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    
    # Structured Address Fields
    mobile_number = models.CharField(max_length=20, blank=True, null=True)
    country_region = models.CharField(max_length=100, blank=True, null=True)
    house_info = models.CharField("Flat, House no, Building, etc.", max_length=255, blank=True, null=True)
    street_info = models.CharField("Area, Street, Sector, Village", max_length=255, blank=True, null=True)
    landmark = models.CharField(max_length=255, blank=True, null=True)
    pincode = models.CharField(max_length=20, blank=True, null=True)
    city = models.CharField("Town/City", max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    
    # Legacy field for compatibility
    address = models.TextField(blank=True, null=True)
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    rejection_reason = models.TextField("Rejection Reason", blank=True, null=True)
    # Payment verification fields
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    payment_screenshot = models.ImageField(upload_to='payments/', blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.id} - {self.full_name}"
    
    class Meta:
        ordering = ['-created_at']
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=200, blank=True, default='')
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2) 
    selected_options = models.JSONField(default=dict, blank=True)

    def __str__(self):
        name = self.product_name or (self.product.name if self.product else 'Deleted Product')
        return f"{self.quantity} x {name} (Order {self.order.id})"
    
class OTPRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        expiration_time = self.created_at + timezone.timedelta(minutes=10)
        return timezone.now() <= expiration_time and not self.is_used
    
class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')

    def __str__(self):
        return f"{self.rating} Stars by {self.user.username} on {self.product.name}"
    
class SavedAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_addresses')
    full_name = models.CharField("Full Name", max_length=200)
    email = models.EmailField("Email")
    
    mobile_number = models.CharField(max_length=20, blank=True, null=True)
    country_region = models.CharField(max_length=100, blank=True, null=True)
    house_info = models.CharField("Flat, House no, Building, etc.", max_length=255, blank=True, null=True)
    street_info = models.CharField("Area, Street, Sector, Village", max_length=255, blank=True, null=True)
    landmark = models.CharField(max_length=255, blank=True, null=True)
    pincode = models.CharField(max_length=20, blank=True, null=True)
    city = models.CharField("Town/City", max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    
    is_default = models.BooleanField(default=False)
    
    address = models.TextField("Full Delivery Address (Legacy)", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.is_default:
            SavedAddress.objects.filter(user=self.user).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} - {self.city}, {self.state}"

class ProductAttribute(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    attribute = models.ForeignKey(ProductAttribute, on_delete=models.CASCADE)
    value = models.CharField(max_length=100)
    price_modifier = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} - {self.attribute.name}: {self.value}"

class ShoppableVideo(models.Model):
    title = models.CharField(max_length=200)
    video_file = models.FileField(upload_to='videos/')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='shoppable_videos')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Video: {self.title} for {self.product.name}"