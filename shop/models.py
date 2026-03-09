from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

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
    brand_name = models.CharField(max_length=100, blank=True, null=True)
    specifications = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name

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
    ]

    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    address = models.TextField()
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
    
# Add this right below your Order class in models.py

class OrderItem(models.Model):
    # Links to the specific order
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    # Links to the specific product (using PROTECT so you can't delete a product if an order relies on it)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    
    quantity = models.PositiveIntegerField(default=1)
    # We save the price at the time of purchase in case you change the product price later!
    price = models.DecimalField(max_digits=10, decimal_places=2) 

    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Order {self.order.id})"
    
class OTPRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        # OTP expires after 10 minutes
        expiration_time = self.created_at + timezone.timedelta(minutes=10)
        return timezone.now() <= expiration_time and not self.is_used
    
class Review(models.Model):
    # Links to the product being reviewed
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    # Links to the user who wrote the review
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Restricts the rating to be strictly between 1 and 5 stars
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # CRITICAL: This prevents a user from reviewing the same product twice
        unique_together = ('product', 'user')

    def __str__(self):
        return f"{self.rating} Stars by {self.user.username} on {self.product.name}"
    
# Add this near your other models
class SavedAddress(models.Model):
    # Links this address strictly to the logged-in user
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_addresses')
    full_name = models.CharField("Full Name", max_length=200)
    email = models.EmailField("Email")
    address = models.TextField("Full Delivery Address")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.address[:30]}"

class ProductAttribute(models.Model):
    """Examples: Length, Color, Reel Series, Weight"""
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class ProductVariant(models.Model):
    """The specific choice: '6ft', 'Blue', '3000 Series'"""
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    attribute = models.ForeignKey(ProductAttribute, on_delete=models.CASCADE)
    value = models.CharField(max_length=100) # e.g., '6ft'
    price_modifier = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} - {self.attribute.name}: {self.value}"