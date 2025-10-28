"""
Административная панель для приложения accounts
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User, UserProfile, Address, Wishlist, CompareList, DiscountCode, UserDiscount


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Административная панель для модели User
    """
    list_display = (
        'username', 'email', 'get_full_name', 'phone',
        'is_active', 'is_staff', 'is_subscribed',
        'bonus_points', 'total_spent', 'date_joined'
    )
    list_filter = (
        'is_active', 'is_staff', 'is_superuser',
        'is_subscribed', 'preferred_language', 'date_joined'
    )
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')
    readonly_fields = ('date_joined', 'last_login', 'password')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Дополнительная информация', {
            'fields': ('phone', 'date_of_birth', 'preferred_language')
        }),
        ('Подписки', {
            'fields': ('is_subscribed',)
        }),
        ('Бонусная система', {
            'fields': ('bonus_points', 'total_spent'),
            'classes': ('collapse',)
        }),
    )
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Полное имя'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Административная панель для модели UserProfile
    """
    list_display = (
        'user', 'country', 'city', 'avatar_preview',
        'email_notifications', 'sms_notifications', 'push_notifications'
    )
    list_filter = (
        'email_notifications', 'sms_notifications', 'push_notifications',
        'preferred_payment_method', 'country'
    )
    search_fields = ('user__username', 'user__email', 'city')
    
    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width: 50px; height: auto;">',
                obj.avatar.url
            )
        return "Нет изображения"
    avatar_preview.short_description = 'Аватар'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Address
    """
    list_display = (
        'user', 'type', 'full_name', 'phone', 'city',
        'street', 'is_default', 'created_at'
    )
    list_filter = ('type', 'is_default', 'country', 'city')
    search_fields = ('user__username', 'user__email', 'full_name', 'phone', 'city')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Wishlist
    """
    list_display = ('user', 'product', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'product__name')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'product')


@admin.register(CompareList)
class CompareListAdmin(admin.ModelAdmin):
    """
    Административная панель для модели CompareList
    """
    list_display = ('user', 'product', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'product__name')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'product')


@admin.register(DiscountCode)
class DiscountCodeAdmin(admin.ModelAdmin):
    """
    Административная панель для модели DiscountCode
    """
    list_display = (
        'code', 'description', 'discount_type', 'value',
        'is_active', 'valid_from', 'valid_until', 'current_uses'
    )
    list_filter = (
        'discount_type', 'is_active', 'valid_from', 'valid_until'
    )
    search_fields = ('code', 'description')
    readonly_fields = ('current_uses', 'created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('code', 'description', 'discount_type', 'value')
        }),
        ('Ограничения', {
            'fields': ('max_uses', 'current_uses', 'min_order_amount')
        }),
        ('Период действия', {
            'fields': ('valid_from', 'valid_until')
        }),
        ('Статус', {
            'fields': ('is_active',)
        }),
    )


@admin.register(UserDiscount)
class UserDiscountAdmin(admin.ModelAdmin):
    """
    Административная панель для модели UserDiscount
    """
    list_display = (
        'user', 'discount', 'order', 'discount_amount', 'used_at'
    )
    list_filter = ('used_at', 'discount__discount_type')
    search_fields = ('user__username', 'user__email', 'discount__code')
    readonly_fields = ('used_at',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'discount', 'order')