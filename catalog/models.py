"""
Модели каталога товаров для интернет-магазина мобильных телефонов
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    """
    Категории товаров (смартфоны, аксессуары, умные часы и т.д.)
    """
    name = models.CharField('Название', max_length=100, unique=True)
    slug = models.SlugField('URL-идентификатор', max_length=100, unique=True)
    description = models.TextField('Описание', blank=True)
    image = models.ImageField('Изображение', upload_to='categories/', null=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    # Настройки отображения
    is_active = models.BooleanField('Активна', default=True)
    sort_order = models.PositiveIntegerField('Порядок сортировки', default=0)
    
    # SEO поля
    meta_title = models.CharField('Meta заголовок', max_length=60, blank=True)
    meta_description = models.CharField('Meta описание', max_length=160, blank=True)
    
    # Метаданные
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена', auto_now=True)
    
    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('catalog:category_detail', kwargs={'slug': self.slug})
    
    @property
    def is_parent(self):
        return self.parent is None
    
    @property
    def children_categories(self):
        return self.children.filter(is_active=True)
    
    def get_product_count(self):
        return self.products.filter(is_active=True).count()


class Brand(models.Model):
    """
    Бренды мобильных телефонов (Apple, Samsung, Xiaomi и т.д.)
    """
    name = models.CharField('Название', max_length=100, unique=True)
    slug = models.SlugField('URL-идентификатор', max_length=100, unique=True)
    description = models.TextField('Описание', blank=True)
    logo = models.ImageField('Логотип', upload_to='brands/', null=True, blank=True)
    website = models.URLField('Веб-сайт', blank=True)
    
    # Статистика
    product_count = models.PositiveIntegerField('Количество товаров', default=0)
    
    # Настройки отображения
    is_active = models.BooleanField('Активен', default=True)
    sort_order = models.PositiveIntegerField('Порядок сортировки', default=0)
    
    # Метаданные
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена', auto_now=True)
    
    class Meta:
        verbose_name = 'Бренд'
        verbose_name_plural = 'Бренды'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('catalog:brand_detail', kwargs={'slug': self.slug})


class ProductSpecification(models.Model):
    """
    Характеристики товаров (оперативная память, процессор, экран и т.д.)
    """
    name = models.CharField('Название характеристики', max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='specifications')
    
    # Тип значения характеристики
    VALUE_TYPES = [
        ('text', 'Текст'),
        ('number', 'Число'),
        ('boolean', 'Да/Нет'),
        ('list', 'Список'),
    ]
    value_type = models.CharField('Тип значения', max_length=20, choices=VALUE_TYPES, default='text')
    
    # Единица измерения (ГБ, МБ, ГГц и т.д.)
    unit = models.CharField('Единица измерения', max_length=20, blank=True)
    
    # Настройки отображения
    sort_order = models.PositiveIntegerField('Порядок сортировки', default=0)
    
    # Метаданные
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена', auto_now=True)
    
    class Meta:
        verbose_name = 'Характеристика'
        verbose_name_plural = 'Характеристики'
        unique_together = ('name', 'category')
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.category.name})"


class Product(models.Model):
    """
    Основная модель товара
    """
    # Основная информация
    name = models.CharField('Название товара', max_length=200)
    slug = models.SlugField('URL-идентификатор', max_length=200)
    sku = models.CharField('Артикул', max_length=50, unique=True)
    
    # Связи
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products')
    
    # Описание
    short_description = models.CharField('Краткое описание', max_length=500, blank=True)
    description = models.TextField('Подробное описание', blank=True)
    specifications_text = models.TextField('Характеристики (текст)', blank=True)
    
    # Цены
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    old_price = models.DecimalField('Старая цена', max_digits=10, decimal_places=2, null=True, blank=True)
    cost_price = models.DecimalField('Себестоимость', max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Наличие
    stock_quantity = models.PositiveIntegerField('Количество на складе', default=0)
    in_stock = models.BooleanField('В наличии', default=True)
    is_available = models.BooleanField('Доступен для заказа', default=True)
    
    # Доставка
    free_delivery = models.BooleanField('Бесплатная доставка', default=False)
    delivery_time = models.CharField('Время доставки', max_length=50, default='1-3 дня')
    
    # Гарантия и сервис
    warranty_months = models.PositiveIntegerField('Гарантия (месяцев)', default=12)
    is_official_warranty = models.BooleanField('Официальная гарантия', default=True)
    
    # Статистика
    views_count = models.PositiveIntegerField('Просмотры', default=0)
    sales_count = models.PositiveIntegerField('Продажи', default=0)
    rating = models.DecimalField('Рейтинг', max_digits=3, decimal_places=2, default=0)
    reviews_count = models.PositiveIntegerField('Количество отзывов', default=0)
    
    # Настройки отображения
    is_active = models.BooleanField('Активен', default=True)
    is_featured = models.BooleanField('Рекомендуемый', default=False)
    is_bestseller = models.BooleanField('Хит продаж', default=False)
    is_new = models.BooleanField('Новинка', default=False)
    is_discount = models.BooleanField('Со скидкой', default=False, null=False)
    
    sort_order = models.PositiveIntegerField('Порядок сортировки', default=0)
    
    # SEO поля
    meta_title = models.CharField('Meta заголовок', max_length=60, blank=True)
    meta_description = models.CharField('Meta описание', max_length=160, blank=True)
    
    # Метаданные
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    
    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['sort_order', '-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['sku']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['category', 'brand']),
            models.Index(fields=['is_active', 'is_featured']),
        ]
    
    def __str__(self):
        return f"{self.brand.name} {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.brand.name}-{self.name}")
        
        # Автоматически определять статус наличия
        self.in_stock = self.stock_quantity > 0
        self.is_available = self.in_stock and self.is_active
        
        # Определять статус новинки
        from django.utils import timezone
        if self.created_at:
            days_since_created = (timezone.now() - self.created_at).days
            self.is_new = days_since_created <= 30
        else:
            self.is_new = True  # Для новых товаров считаем их новинками
        
        # Определять статус скидки
        self.is_discount = self.old_price and self.old_price > self.price
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('catalog:product_detail', kwargs={'slug': self.slug})
    
    def get_discount_percent(self):
        """Рассчитать процент скидки"""
        if self.old_price and self.old_price > self.price:
            return int(((self.old_price - self.price) / self.old_price) * 100)
        return 0
    
    def get_main_image(self):
        """Получить основное изображение товара"""
        main_image = self.images.filter(is_main=True).first()
        return main_image.image if main_image else None
    
    def get_all_images(self):
        """Получить все изображения товара"""
        return self.images.all()
    
    def get_specifications(self):
        """Получить характеристики товара"""
        return self.specifications.all()
    
    def get_related_products(self):
        """Получить похожие товары"""
        return Product.objects.filter(
            category=self.category,
            brand=self.brand,
            is_active=True
        ).exclude(id=self.id)[:4]
    
    def can_buy(self):
        """Проверить, можно ли купить товар"""
        return self.is_available and self.stock_quantity > 0


class ProductImage(models.Model):
    """
    Изображения товаров
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField('Изображение', upload_to='products/')
    alt_text = models.CharField('Alt текст', max_length=100, blank=True)
    is_main = models.BooleanField('Основное изображение', default=False)
    sort_order = models.PositiveIntegerField('Порядок сортировки', default=0)
    
    # Метаданные
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена', auto_now=True)
    
    class Meta:
        verbose_name = 'Изображение товара'
        verbose_name_plural = 'Изображения товаров'
        ordering = ['sort_order', 'created_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.alt_text or 'Изображение'}"
    
    def save(self, *args, **kwargs):
        # Если это основное изображение, снять галочку с других
        if self.is_main:
            ProductImage.objects.filter(product=self.product).update(is_main=False)
        super().save(*args, **kwargs)


class ProductSpecificationValue(models.Model):
    """
    Значения характеристик для товаров
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='specifications')
    specification = models.ForeignKey(ProductSpecification, on_delete=models.CASCADE)
    value_text = models.CharField('Текстовое значение', max_length=200, blank=True)
    value_number = models.DecimalField('Числовое значение', max_digits=10, decimal_places=2, null=True, blank=True)
    value_boolean = models.BooleanField('Булево значение', default=False)
    value_list = models.CharField('Значение из списка', max_length=200, blank=True)
    
    class Meta:
        verbose_name = 'Значение характеристики'
        verbose_name_plural = 'Значения характеристик'
        unique_together = ('product', 'specification')
        ordering = ['specification__sort_order', 'specification__name']
    
    def __str__(self):
        return f"{self.product.name} - {self.specification.name}: {self.get_value()}"
    
    def get_value(self):
        """Получить значение в зависимости от типа"""
        spec = self.specification
        if spec.value_type == 'text':
            return self.value_text
        elif spec.value_type == 'number':
            if spec.unit:
                return f"{self.value_number} {spec.unit}"
            return str(self.value_number)
        elif spec.value_type == 'boolean':
            return 'Да' if self.value_boolean else 'Нет'
        elif spec.value_type == 'list':
            if spec.unit:
                return f"{self.value_list} {spec.unit}"
            return self.value_list
        return self.value_text


class Review(models.Model):
    """
    Отзывы пользователей о товарах
    """
    RATING_CHOICES = [
        (1, '1 - Очень плохо'),
        (2, '2 - Плохо'),
        (3, '3 - Удовлетворительно'),
        (4, '4 - Хорошо'),
        (5, '5 - Отлично'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='reviews')
    
    # Основные поля отзыва
    rating = models.PositiveIntegerField('Рейтинг', choices=RATING_CHOICES)
    title = models.CharField('Заголовок отзыва', max_length=200, blank=True)
    text = models.TextField('Текст отзыва')
    pros = models.TextField('Достоинства', blank=True)
    cons = models.TextField('Недостатки', blank=True)
    
    # Статус модерации
    is_approved = models.BooleanField('Одобрен', default=False)
    is_verified_purchase = models.BooleanField('Проверенная покупка', default=False)
    
    # Полезность отзыва
    helpful_count = models.PositiveIntegerField('Полезно', default=0)
    unhelpful_count = models.PositiveIntegerField('Не полезно', default=0)
    
    # Метаданные
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    
    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']
        unique_together = ('product', 'user')  # Один отзыв на товар от пользователя
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.product.name} ({self.rating}★)"


class ReviewHelpfulness(models.Model):
    """
    Голосования за полезность отзывов
    """
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    is_helpful = models.BooleanField('Полезен')
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Голос за полезность'
        verbose_name_plural = 'Голоса за полезность'
        unique_together = ('review', 'user')
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.review.title}"


class ProductStatistic(models.Model):
    """
    Статистика просмотров товаров
    """
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='statistics')
    
    # Статистика просмотров
    total_views = models.PositiveIntegerField('Всего просмотров', default=0)
    daily_views = models.PositiveIntegerField('Просмотров сегодня', default=0)
    weekly_views = models.PositiveIntegerField('Просмотров за неделю', default=0)
    monthly_views = models.PositiveIntegerField('Просмотров за месяц', default=0)
    
    # Статистика продаж
    total_sales = models.PositiveIntegerField('Всего продаж', default=0)
    daily_sales = models.PositiveIntegerField('Продаж сегодня', default=0)
    weekly_sales = models.PositiveIntegerField('Продаж за неделю', default=0)
    monthly_sales = models.PositiveIntegerField('Продаж за месяц', default=0)
    
    # Статистика избранного и сравнения
    wishlist_count = models.PositiveIntegerField('В избранном', default=0)
    compare_count = models.PositiveIntegerField('В сравнении', default=0)
    
    # Обновлено
    updated_at = models.DateTimeField('Обновлена', auto_now=True)
    
    class Meta:
        verbose_name = 'Статистика товара'
        verbose_name_plural = 'Статистика товаров'
    
    def __str__(self):
        return f"Статистика {self.product.name}"
