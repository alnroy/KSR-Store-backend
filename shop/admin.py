from django.contrib import admin
from django.utils.html import format_html  # <--- This fixes the Unresolved Import
from .models import Category, Product, Order

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # This defines what the admin sees in the list view
    list_display = ('display_image', 'name', 'category', 'price', 'stock_status')
    list_filter = ('category',)
    search_fields = ('name',)

    # 1. Show the actual image in the list!
    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 50px; height: 50px; border-radius: 8px;" />', obj.image.url)
        return "No Image"
    display_image.short_description = 'Preview'

    # 2. Make stock levels easy to read (Green for good, Red for low)
    def stock_status(self, obj):
        if obj.stock <= 5:
            return format_html('<b style="color: red;">Low Stock: {}</b>', obj.stock)
        return format_html('<b style="color: green;">In Stock: {}</b>', obj.stock)
    stock_status.short_description = 'Stock Level'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # 'status' MUST be here for 'list_editable' to work
    list_display = ('id', 'full_name', 'total_amount', 'status', 'colored_status', 'view_payment')
    
    # This allows the non-tech admin to change status with one click
    list_editable = ('status',) 
    
    readonly_fields = ('payment_preview',)

    def colored_status(self, obj):
        # This acts as a visual guide next to the editable dropdown
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