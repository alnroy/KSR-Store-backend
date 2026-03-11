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
    list_display = ('id', 'full_name', 'total_amount', 'status', 'colored_status', 'view_payment')
    list_editable = ('status',) 
    readonly_fields = ('payment_preview',)

    def colored_status(self, obj):
        colors = {
            'PAID': 'green',
            'PENDING': 'orange',
            'FAILED': 'red',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px;">Current: {}</span>', 
            colors.get(obj.status, 'gray'), obj.status
        )
    colored_status.short_description = 'Visual Indicator'

    def view_payment(self, obj):
        if obj.payment_screenshot:
            return format_html('<a href="{}" target="_blank">View Screenshot</a>', obj.payment_screenshot.url)
        return "No Proof"

    def payment_preview(self, obj):
        if obj.payment_screenshot:
            return format_html('<img src="{}" style="max-width: 300px;" />', obj.payment_screenshot.url)
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
    list_display = ('user', 'full_name', 'email', 'address')
    search_fields = ('full_name', 'email', 'user__username')

@admin.register(ShoppableVideo)
class ShoppableVideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'product', 'created_at')
    list_filter = ('product', 'created_at')
    search_fields = ('title', 'product__name')
