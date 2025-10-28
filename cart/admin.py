"""
Административная панель для приложения cart
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Cart, CartItem, CartSession, RecentlyViewed, SavedForLater, CartAnalytics, CartAbandonment, BulkCartAction


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Cart
    """
    list_display = (
        'id', 'get_user_display', 'session_key', 'items_count',
        'total_price', 'final_price', 'is_active', 'is_completed',
        'last_activity'
    )
    list_filter = (
        'is_active', 'is_completed', 'created_at', 'updated_at'
    )
    search_fields = ('session_key', 'user__username', 'user__email')
    readonly_fields = (
        'created_at', 'updated_at', 'last_activity',
        'items_count', 'total_quantity', 'subtotal',
        'total_discount', 'final_price'
    )
    
    fieldsets = (
        ('Идентификация', {
            'fields': ('session_key', 'user', 'is_active', 'is_completed')
        }),
        ('Продукты', {
            'fields': ('items_count', 'total_quantity')
        }),
        ('Цены', {
            'fields': ('subtotal', 'total_discount', 'final_price')
        }),
        ('Скидки', {
            'fields': ('applied_discount', 'discount_amount')
        }),
        ('Доставка', {
            'fields': ('delivery_cost', 'free_delivery_threshold')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at', 'last_activity'),
            'classes': ('collapse',)
        }),
    )
    
    def get_user_display(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return f"Гость ({obj.session_key[:10]}...)"
    get_user_display.short_description = 'Пользователь'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """
    Административная панель для модели CartItem
    """
    list_display = (
        'cart', 'product_name', 'quantity', 'unit_price',
        'total_price', 'discount_amount', 'added_at', 'is_active'
    )
    list_filter = ('is_active', 'added_at')
    search_fields = (
        'cart__session_key', 'cart__user__username',
        'product_name', 'product_sku', 'product_brand'
    )
    readonly_fields = ('added_at',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('cart', 'cart__user', 'product')


@admin.register(CartSession)
class CartSessionAdmin(admin.ModelAdmin):
    """
    Административная панель для модели CartSession
    """
    list_display = (
        'session_key', 'cart', 'ip_address',
        'created_at', 'last_activity'
    )
    list_filter = ('created_at', 'last_activity')
    search_fields = ('session_key', 'ip_address')
    readonly_fields = ('created_at', 'last_activity')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('cart')


@admin.register(RecentlyViewed)
class RecentlyViewedAdmin(admin.ModelAdmin):
    """
    Административная панель для модели RecentlyViewed
    """
    list_display = ('user', 'product', 'viewed_at')
    list_filter = ('viewed_at',)
    search_fields = ('user__username', 'user__email', 'product__name')
    readonly_fields = ('viewed_at',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'product')


@admin.register(SavedForLater)
class SavedForLaterAdmin(admin.ModelAdmin):
    """
    Административная панель для модели SavedForLater
    """
    list_display = ('user', 'product', 'quantity', 'unit_price', 'saved_at')
    list_filter = ('saved_at',)
    search_fields = ('user__username', 'user__email', 'product__name')
    readonly_fields = ('saved_at',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'product')


@admin.register(CartAnalytics)
class CartAnalyticsAdmin(admin.ModelAdmin):
    """
    Административная панель для модели CartAnalytics
    """
    list_display = (
        'session_key', 'user', 'cart_value', 'items_count',
        'conversion_stage', 'created_at'
    )
    list_filter = ('conversion_stage', 'created_at')
    search_fields = ('session_key', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(CartAbandonment)
class CartAbandonmentAdmin(admin.ModelAdmin):
    """
    Административная панель для модели CartAbandonment
    """
    list_display = (
        'cart', 'abandonment_reason', 'email', 'phone',
        'recovery_sent', 'recovered', 'abandoned_at'
    )
    list_filter = ('recovery_sent', 'recovered', 'abandoned_at')
    search_fields = (
        'cart__session_key', 'cart__user__username',
        'email', 'phone'
    )
    readonly_fields = ('abandoned_at', 'recovered_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('cart', 'cart__user')


@admin.register(BulkCartAction)
class BulkCartActionAdmin(admin.ModelAdmin):
    """
    Административная панель для модели BulkCartAction
    """
    list_display = (
        'user', 'action_type', 'status', 'created_at', 'completed_at'
    )
    list_filter = ('action_type', 'status', 'created_at')
    search_fields = ('user__username', 'action_type')
    readonly_fields = ('created_at', 'completed_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')