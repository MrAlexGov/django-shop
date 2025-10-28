"""
Административная панель для приложения catalog
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Category, Brand, Product, ProductImage, ProductSpecification, ProductSpecificationValue, Review, ReviewHelpfulness, ProductStatistic


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Category
    """
    list_display = (
        'name', 'parent', 'is_active', 
        'sort_order', 'product_count_display', 'created_at'
    )
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'parent', 'description', 'image')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Настройки', {
            'fields': ('is_active', 'sort_order')
        }),
    )
    
    def product_count_display(self, obj):
        return obj.get_product_count()
    product_count_display.short_description = 'Количество товаров'


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Brand
    """
    list_display = (
        'name', 'logo_preview', 'website', 
        'is_active', 'product_count', 'sort_order'
    )
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'logo', 'website')
        }),
        ('Статистика', {
            'fields': ('product_count',),
            'classes': ('collapse',)
        }),
        ('Настройки', {
            'fields': ('is_active', 'sort_order')
        }),
    )
    
    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="width: 50px; height: auto;">',
                obj.logo.url
            )
        return "Нет изображения"
    logo_preview.short_description = 'Логотип'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Product
    """
    list_display = (
        'name', 'brand', 'category', 'price', 'old_price',
        'is_active', 'is_featured', 'is_bestseller', 
        'in_stock', 'stock_quantity', 'rating', 'views_count'
    )
    list_filter = (
        'is_active', 'is_featured', 'is_bestseller', 
        'is_new', 'in_stock', 'brand', 'category',
        'warranty_months', 'free_delivery'
    )
    search_fields = ('name', 'sku', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = (
        'views_count', 'sales_count', 'rating', 'reviews_count',
        'created_at', 'updated_at'
    )
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'sku', 'brand', 'category')
        }),
        ('Описание', {
            'fields': ('short_description', 'description')
        }),
        ('Цены', {
            'fields': ('price', 'old_price', 'cost_price')
        }),
        ('Наличие', {
            'fields': ('stock_quantity', 'in_stock', 'is_available')
        }),
        ('Доставка и сервис', {
            'fields': ('free_delivery', 'delivery_time', 'warranty_months', 'is_official_warranty')
        }),
        ('Статистика', {
            'fields': ('views_count', 'sales_count', 'rating', 'reviews_count'),
            'classes': ('collapse',)
        }),
        ('Настройки отображения', {
            'fields': ('is_active', 'is_featured', 'is_bestseller', 'is_new', 'sort_order')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('brand', 'category')
    
    def get_discount_percent(self, obj):
        if obj.old_price and obj.old_price > obj.price:
            return f"{obj.get_discount_percent()}%"
        return "-"
    get_discount_percent.short_description = 'Скидка'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """
    Административная панель для модели ProductImage
    """
    list_display = (
        'product', 'image_preview', 'alt_text', 
        'is_main', 'sort_order', 'created_at'
    )
    list_filter = ('is_main', 'created_at')
    search_fields = ('product__name', 'alt_text')
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: auto;">',
                obj.image.url
            )
        return "Нет изображения"
    image_preview.short_description = 'Изображение'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('product')


@admin.register(ProductSpecification)
class ProductSpecificationAdmin(admin.ModelAdmin):
    """
    Административная панель для модели ProductSpecification
    """
    list_display = (
        'name', 'category', 'value_type', 
        'unit', 'sort_order'
    )
    list_filter = ('value_type', 'category')
    search_fields = ('name', 'category__name')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'category', 'value_type', 'unit')
        }),
        ('Настройки', {
            'fields': ('sort_order',)
        }),
    )


@admin.register(ProductSpecificationValue)
class ProductSpecificationValueAdmin(admin.ModelAdmin):
    """
    Административная панель для модели ProductSpecificationValue
    """
    list_display = (
        'product', 'specification', 'get_value'
    )
    list_filter = ('specification__value_type', 'specification__category')
    search_fields = ('product__name', 'specification__name')
    
    def get_value(self, obj):
        return obj.get_value()
    get_value.short_description = 'Значение'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('product', 'specification')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Review
    """
    list_display = (
        'product', 'user', 'rating', 'title', 
        'is_approved', 'is_verified_purchase', 
        'helpful_count', 'created_at'
    )
    list_filter = (
        'rating', 'is_approved', 'is_verified_purchase', 
        'created_at'
    )
    search_fields = (
        'product__name', 'user__username', 
        'user__first_name', 'user__last_name',
        'title', 'text'
    )
    readonly_fields = (
        'helpful_count', 'unhelpful_count', 
        'created_at', 'updated_at'
    )
    
    fieldsets = (
        (None, {
            'fields': ('product', 'user', 'rating', 'title')
        }),
        ('Текст отзыва', {
            'fields': ('text', 'pros', 'cons')
        }),
        ('Статус модерации', {
            'fields': ('is_approved', 'is_verified_purchase')
        }),
        ('Полезность', {
            'fields': ('helpful_count', 'unhelpful_count'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('product', 'user')


@admin.register(ReviewHelpfulness)
class ReviewHelpfulnessAdmin(admin.ModelAdmin):
    """
    Административная панель для модели ReviewHelpfulness
    """
    list_display = ('review', 'user', 'is_helpful', 'created_at')
    list_filter = ('is_helpful', 'created_at')
    search_fields = (
        'review__title', 'user__username', 
        'user__first_name', 'user__last_name'
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('review', 'user')


@admin.register(ProductStatistic)
class ProductStatisticAdmin(admin.ModelAdmin):
    """
    Административная панель для модели ProductStatistic
    """
    list_display = (
        'product', 'total_views', 'total_sales', 
        'wishlist_count', 'compare_count', 'updated_at'
    )
    list_filter = ('updated_at',)
    search_fields = ('product__name', 'product__sku')
    readonly_fields = ('updated_at',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('product')


# Кастомный фильтр для товаров по наличию скидки
class DiscountedProductFilter(admin.SimpleListFilter):
    """
    Фильтр для товаров со скидкой
    """
    title = 'Товары со скидкой'
    parameter_name = 'discounted'
    
    def lookups(self, request, model_admin):
        return (
            ('yes', 'Со скидкой'),
            ('no', 'Без скидки'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(old_price__isnull=False, old_price__gt=0)
        elif self.value() == 'no':
            return queryset.filter(old_price__isnull=True) | queryset.filter(old_price=0)
        return queryset


# Расширенная админка для Product с дополнительными фильтрами
class ProductAdminExtended(ProductAdmin):
    """
    Расширенная админка для товаров с дополнительными фильтрами
    """
    list_filter = ProductAdmin.list_filter + (DiscountedProductFilter,)
    
    actions = ['mark_as_featured', 'mark_as_bestseller', 'export_to_csv']
    
    def mark_as_featured(self, request, queryset):
        """Отметить товары как рекомендуемые"""
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} товаров отмечены как рекомендуемые.')
    mark_as_featured.short_description = 'Отметить как рекомендуемые'
    
    def mark_as_bestseller(self, request, queryset):
        """Отметить товары как хит продаж"""
        updated = queryset.update(is_bestseller=True)
        self.message_user(request, f'{updated} товаров отмечены как хит продаж.')
    mark_as_bestseller.short_description = 'Отметить как хит продаж'
    
    def export_to_csv(self, request, queryset):
        """Экспорт товаров в CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="products.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Название', 'Артикул', 'Бренд', 'Категория', 'Цена', 'В наличии'])
        
        for product in queryset:
            writer.writerow([
                product.name,
                product.sku,
                product.brand.name,
                product.category.name,
                product.price,
                product.stock_quantity
            ])
        
        return response
    export_to_csv.short_description = 'Экспортировать в CSV'


# Перерегистрируем Product с расширенной админкой
admin.site.unregister(Product)
admin.site.register(Product, ProductAdminExtended)
