"""
Административная панель для приложения core
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import SiteSettings, Banner, Slider, ContactForm, SearchLog, Page, Notification, Feedback


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """
    Административная панель для модели SiteSettings
    """
    list_display = ('site_name', 'maintenance_mode', 'updated_at')
    list_filter = ('maintenance_mode', 'allow_user_registration', 'allow_reviews')
    
    fieldsets = (
        ('Основная информация', {
            'fields': (
                'site_name', 'site_description', 
                'site_logo', 'favicon'
            )
        }),
        ('Контактная информация', {
            'fields': (
                'contact_phone', 'contact_email', 'contact_address'
            )
        }),
        ('Социальные сети', {
            'fields': (
                'social_vk', 'social_telegram', 
                'social_whatsapp'
            )
        }),
        ('Настройки магазина', {
            'fields': (
                'default_currency', 'tax_rate', 
                'min_free_delivery_amount', 'delivery_cost'
            )
        }),
        ('Бонусная система', {
            'fields': (
                'bonus_rate', 'points_per_ruble'
            ),
            'classes': ('collapse',)
        }),
        ('Безопасность', {
            'fields': (
                'password_min_length', 
                'require_phone_verification', 
                'require_email_verification'
            ),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': (
                'google_analytics_id', 'yandex_metrica_id'
            ),
            'classes': ('collapse',)
        }),
        ('Общие настройки', {
            'fields': (
                'maintenance_mode', 'allow_user_registration', 
                'allow_reviews'
            )
        }),
    )
    
    def has_add_permission(self, request):
        """Разрешить добавлять только если настроек еще нет"""
        return not SiteSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """Запретить удаление настроек"""
        return False


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Banner
    """
    list_display = (
        'title', 'banner_type', 'category', 'product',
        'is_active', 'sort_order', 'start_date', 'end_date'
    )
    list_filter = (
        'banner_type', 'is_active', 'start_date', 'end_date'
    )
    search_fields = ('title', 'subtitle', 'description')
    
    fieldsets = (
        (None, {
            'fields': ('title', 'subtitle', 'description', 'image')
        }),
        ('Ссылка', {
            'fields': ('link_url', 'link_text')
        }),
        ('Настройки отображения', {
            'fields': ('banner_type', 'is_active', 'sort_order')
        }),
        ('Связи', {
            'fields': ('category', 'product')
        }),
        ('Период показа', {
            'fields': ('start_date', 'end_date'),
            'classes': ('collapse',)
        }),
    )
    
    autocomplete_fields = ('category', 'product')


@admin.register(Slider)
class SliderAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Slider
    """
    list_display = (
        'title', 'is_active', 'sort_order', 
        'start_date', 'end_date'
    )
    list_filter = ('is_active', 'start_date', 'end_date')
    search_fields = ('title', 'subtitle', 'description')
    
    fieldsets = (
        (None, {
            'fields': ('title', 'subtitle', 'description', 'image')
        }),
        ('Ссылка', {
            'fields': ('link_url', 'link_text')
        }),
        ('Настройки отображения', {
            'fields': ('is_active', 'sort_order')
        }),
        ('Стили', {
            'fields': ('text_color', 'overlay_opacity')
        }),
        ('Период показа', {
            'fields': ('start_date', 'end_date'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ContactForm)
class ContactFormAdmin(admin.ModelAdmin):
    """
    Административная панель для модели ContactForm
    """
    list_display = (
        'name', 'email', 'subject', 'status',
        'assigned_to', 'created_at'
    )
    list_filter = (
        'subject', 'status', 'assigned_to', 'created_at'
    )
    search_fields = ('name', 'email', 'phone', 'message')
    readonly_fields = (
        'ip_address', 'user_agent', 
        'created_at', 'updated_at'
    )
    
    fieldsets = (
        (None, {
            'fields': ('name', 'email', 'phone', 'subject', 'message')
        }),
        ('Статус', {
            'fields': ('status', 'assigned_to')
        }),
        ('Ответ', {
            'fields': ('admin_response', 'responded_at', 'responded_by')
        }),
        ('Техническая информация', {
            'fields': ('ip_address', 'user_agent', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['assign_to_me', 'mark_as_answered']
    
    def assign_to_me(self, request, queryset):
        """Назначить мне"""
        updated = queryset.update(assigned_to=request.user)
        self.message_user(request, f'{updated} сообщений назначено вам.')
    assign_to_me.short_description = 'Назначить мне'
    
    def mark_as_answered(self, request, queryset):
        """Отметить как отвеченные"""
        from django.utils import timezone
        updated = queryset.update(
            status='answered', 
            responded_at=timezone.now(),
            responded_by=request.user
        )
        self.message_user(request, f'{updated} сообщений отмечено как отвеченные.')
    mark_as_answered.short_description = 'Отметить как отвеченные'


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    """
    Административная панель для модели SearchLog
    """
    list_display = (
        'user', 'query', 'results_count', 
        'searched_at'
    )
    list_filter = ('searched_at', 'results_count')
    search_fields = ('query',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')
    
    def has_add_permission(self, request):
        """Запретить добавление записей поиска вручную"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Запретить редактирование записей поиска"""
        return False


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Page
    """
    list_display = (
        'title', 'slug', 'is_published', 
        'show_in_menu', 'menu_order'
    )
    list_filter = ('is_published', 'show_in_menu')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'content')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Настройки отображения', {
            'fields': ('is_published', 'show_in_menu', 'menu_order')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Notification
    """
    list_display = (
        'user', 'notification_type', 'title', 
        'is_read', 'created_at'
    )
    list_filter = (
        'notification_type', 'is_read', 
        'is_sent_email', 'created_at'
    )
    search_fields = (
        'user__username', 'user__first_name', 
        'user__last_name', 'title', 'message'
    )
    readonly_fields = ('created_at', 'read_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        """Отметить как прочитанные"""
        for notification in queryset:
            notification.mark_as_read()
        self.message_user(request, f'{queryset.count()} уведомлений отмечено как прочитанные.')
    mark_as_read.short_description = 'Отметить как прочитанные'
    
    def mark_as_unread(self, request, queryset):
        """Отметить как непрочитанные"""
        updated = queryset.update(is_read=False, read_at=None)
        self.message_user(request, f'{updated} уведомлений отмечено как непрочитанные.')
    mark_as_unread.short_description = 'Отметить как непрочитанные'


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Feedback
    """
    list_display = (
        'title', 'category', 'status', 
        'assigned_to', 'created_at'
    )
    list_filter = (
        'category', 'status', 'assigned_to', 'created_at'
    )
    search_fields = ('title', 'description', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('user', 'category', 'title', 'description')
        }),
        ('Статус', {
            'fields': ('status', 'assigned_to')
        }),
        ('Ответ', {
            'fields': ('admin_response', 'responded_at', 'responded_by')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['assign_to_me', 'accept_feedback']
    
    def assign_to_me(self, request, queryset):
        """Назначить мне"""
        updated = queryset.update(assigned_to=request.user)
        self.message_user(request, f'{updated} предложений назначено вам.')
    assign_to_me.short_description = 'Назначить мне'
    
    def accept_feedback(self, request, queryset):
        """Принять предложения"""
        updated = queryset.update(status='accepted')
        self.message_user(request, f'{updated} предложений принято.')
    accept_feedback.short_description = 'Принять выбранные'


# Группировка админок по приложениям
admin.site.site_header = "PhoneShop - Административная панель"
admin.site.site_title = "PhoneShop Admin"
admin.site.index_title = "Добро пожаловать в административную панель PhoneShop"

# Кастомные настройки админки
admin.site.enable_nav_sidebar = False
admin.site.enable_nav_sidebar_filter = True

# Настройка пагинации админки
admin.ModelAdmin.list_per_page = 25

# Поиск по полям с автодополнением
admin.site.register_model = {
    'PhoneShop': [
        'Настройки сайта',
        'Баннеры и слайдеры',
        'Статические страницы',
        'Обратная связь',
    ]
}

# Регистрация моделей в порядке логической группировки
admin.site.site_header = "PhoneShop - Административная панель"
admin.site.site_title = "PhoneShop Admin"  
admin.site.index_title = "Панель управления интернет-магазином"
