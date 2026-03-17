from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, Order, ProductAttribute, ProductVariant, Brand, OTPRecord, Review, SavedAddress, ShoppableVideo

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('display_logo', 'name')
    search_fields = ('name',)

    def display_logo(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: contain;" />', obj.logo.url)
        return "No Logo"
    display_logo.short_description = 'Logo'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('display_image', 'name', 'category', 'price', 'stock_status')
    list_filter = ('category',)
    search_fields = ('name',)

    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 50px; height: 50px; border-radius: 8px;" />', obj.image.url)
        return "No Image"
    display_image.short_description = 'Preview'

    def stock_status(self, obj):
        if obj.stock <= 5:
            return format_html('<b style="color: red;">Low Stock: {}</b>', obj.stock)
        return format_html('<b style="color: green;">In Stock: {}</b>', obj.stock)
    stock_status.short_description = 'Stock Level'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'email', 'city', 'total_amount', 'status', 'view_payment', 'created_at')
    list_filter = ('status', 'created_at', 'state', 'city')
    search_fields = ('full_name', 'email', 'transaction_id', 'city', 'pincode')
    list_editable = ('status',) 
    
    fieldsets = (
        ('Customer Info', {
            'fields': ('user', 'full_name', 'email', 'mobile_number')
        }),
        ('Shipping Intelligence (Structured)', {
            'fields': (
                'house_info', 'street_info', 'landmark', 
                'city', 'state', 'pincode', 'country_region'
            )
        }),
        ('Legacy Address Copy', {
            'fields': ('address',),
            'classes': ('collapse',)
        }),
        ('Payment Details', {
            'fields': ('total_amount', 'transaction_id', 'payment_screenshot', 'payment_preview')
        }),
        ('Order Status', {
            'fields': ('status', 'rejection_reason')
        }),
    )
    
    readonly_fields = ('payment_preview', 'created_at', 'updated_at')

    def view_payment(self, obj):
        if obj.payment_screenshot:
            return format_html('<a href="{}" target="_blank">View Proof</a>', obj.payment_screenshot.url)
        return "No Proof"

    def payment_preview(self, obj):
        if obj.payment_screenshot:
            return format_html('<img src="{}" style="max-width: 300px; border-radius: 10px; border: 1px solid #ddd;" />', obj.payment_screenshot.url)
        return "No Payment Uploaded"

@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(OTPRecord)
class OTPRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp', 'created_at', 'is_used')
    list_filter = ('is_used', 'created_at')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')

@admin.register(SavedAddress)
class SavedAddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'city', 'state', 'pincode', 'is_default')
    list_filter = ('is_default', 'state', 'city')
    search_fields = ('full_name', 'email', 'user__username', 'city', 'pincode')

@admin.register(ShoppableVideo)
class ShoppableVideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'product', 'created_at')
    list_filter = ('product', 'created_at')
    search_fields = ('title', 'product__name')
