"""
Административная панель для приложения orders
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Order, OrderItem, OrderHistory, Payment, Shipment, OrderReturn, OrderNotification, OrderAnalytics


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Order
    """
    list_display = (
        'order_number', 'user', 'status', 'payment_status',
        'total_amount', 'delivery_method', 'created_at'
    )
    list_filter = (
        'status', 'payment_status', 'order_type',
        'delivery_method', 'payment_method', 'created_at'
    )
    search_fields = ('order_number', 'user__username', 'user__email')
    readonly_fields = (
        'order_number', 'created_at', 'updated_at',
        'confirmed_at', 'shipped_at', 'delivered_at', 'completed_at'
    )
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('order_number', 'user', 'status', 'order_type')
        }),
        ('Суммы', {
            'fields': ('subtotal', 'discount_amount', 'delivery_cost', 'tax_amount', 'total_amount')
        }),
        ('Адреса', {
            'fields': ('billing_address', 'shipping_address')
        }),
        ('Доставка', {
            'fields': ('delivery_method', 'delivery_date', 'delivery_time_slot', 'delivery_comment')
        }),
        ('Оплата', {
            'fields': ('payment_method', 'payment_status', 'payment_reference', 'payment_date')
        }),
        ('Дополнительная информация', {
            'fields': ('customer_note', 'admin_note', 'gift_message', 'gift_wrapping')
        }),
        ('Бонусы', {
            'fields': ('bonus_points_used', 'bonus_points_earned'),
            'classes': ('collapse',)
        }),
        ('Метаданные', {
            'fields': ('ip_address', 'user_agent', 'source'),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at', 'confirmed_at', 'shipped_at', 'delivered_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_confirmed', 'mark_as_shipped', 'mark_as_delivered', 'export_orders_csv']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'billing_address', 'shipping_address')
    
    def mark_as_confirmed(self, request, queryset):
        """Отметить заказы как подтвержденные"""
        updated = queryset.update(status='processing')
        self.message_user(request, f'{updated} заказов отмечены как подтвержденные.')
    mark_as_confirmed.short_description = 'Отметить как подтвержденные'
    
    def mark_as_shipped(self, request, queryset):
        """Отметить заказы как отправленные"""
        updated = queryset.update(status='shipped')
        self.message_user(request, f'{updated} заказов отмечены как отправленные.')
    mark_as_shipped.short_description = 'Отметить как отправленные'
    
    def mark_as_delivered(self, request, queryset):
        """Отметить заказы как доставленные"""
        updated = queryset.update(status='delivered')
        self.message_user(request, f'{updated} заказов отмечены как доставленные.')
    mark_as_delivered.short_description = 'Отметить как доставленные'
    
    def export_orders_csv(self, request, queryset):
        """Экспорт заказов в CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="orders.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Номер заказа', 'Пользователь', 'Статус', 'Сумма', 'Дата создания'])
        
        for order in queryset:
            writer.writerow([
                order.order_number,
                order.user.username,
                order.get_status_display(),
                order.total_amount,
                order.created_at
            ])
        
        return response
    export_orders_csv.short_description = 'Экспортировать в CSV'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """
    Административная панель для модели OrderItem
    """
    list_display = (
        'order', 'product_name', 'quantity',
        'unit_price', 'total_price', 'is_active'
    )
    list_filter = ('is_active', 'is_returned')
    search_fields = ('order__order_number', 'product_name', 'product_sku')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('order')


@admin.register(OrderHistory)
class OrderHistoryAdmin(admin.ModelAdmin):
    """
    Административная панель для модели OrderHistory
    """
    list_display = ('order', 'action', 'user', 'old_status', 'new_status', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('order__order_number', 'action', 'user__username')
    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('order', 'user')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Payment
    """
    list_display = (
        'order', 'payment_method', 'amount', 'currency',
        'status', 'transaction_id', 'created_at'
    )
    list_filter = ('payment_method', 'status', 'currency', 'created_at')
    search_fields = ('order__order_number', 'transaction_id', 'payment_gateway')
    readonly_fields = ('created_at', 'processed_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('order')


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Shipment
    """
    list_display = (
        'order', 'method', 'carrier', 'tracking_number',
        'status', 'estimated_delivery', 'created_at'
    )
    list_filter = ('method', 'status', 'created_at')
    search_fields = ('order__order_number', 'carrier', 'tracking_number')
    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('order')


@admin.register(OrderReturn)
class OrderReturnAdmin(admin.ModelAdmin):
    """
    Административная панель для модели OrderReturn
    """
    list_display = (
        'order', 'order_item', 'reason', 'status',
        'quantity', 'refund_amount', 'requested_at'
    )
    list_filter = ('reason', 'status', 'requested_at')
    search_fields = ('order__order_number', 'order_item__product_name')
    readonly_fields = ('requested_at', 'processed_at', 'refunded_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('order', 'order_item')


@admin.register(OrderNotification)
class OrderNotificationAdmin(admin.ModelAdmin):
    """
    Административная панель для модели OrderNotification
    """
    list_display = (
        'order', 'notification_type', 'channel', 'status',
        'created_at', 'sent_at'
    )
    list_filter = ('notification_type', 'channel', 'status', 'created_at')
    search_fields = ('order__order_number', 'subject', 'message')
    readonly_fields = ('created_at', 'sent_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('order')


@admin.register(OrderAnalytics)
class OrderAnalyticsAdmin(admin.ModelAdmin):
    """
    Административная панель для модели OrderAnalytics
    """
    list_display = (
        'order', 'conversion_source', 'campaign_id',
        'browser', 'device_type', 'created_at'
    )
    list_filter = ('created_at', 'browser', 'os', 'device_type')
    search_fields = ('order__order_number', 'conversion_source', 'campaign_id')
    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('order')