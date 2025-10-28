"""
Общие модели для проекта интернет-магазина
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.utils import timezone
import json

User = get_user_model()


class SiteSettings(models.Model):
    """
    Настройки сайта
    """
    # Основная информация
    site_name = models.CharField('Название сайта', max_length=100, default='PhoneShop')
    site_description = models.TextField('Описание сайта', blank=True)
    site_logo = models.ImageField('Логотип сайта', upload_to='site/', null=True, blank=True)
    favicon = models.ImageField('Иконка сайта', upload_to='site/', null=True, blank=True)
    
    # Контактная информация
    contact_phone = models.CharField('Телефон', max_length=20, blank=True)
    contact_email = models.EmailField('Email', blank=True)
    contact_address = models.TextField('Адрес', blank=True)
    
    # Социальные сети
    social_vk = models.URLField('VK', blank=True)
    social_telegram = models.URLField('Telegram', blank=True)
    social_whatsapp = models.URLField('WhatsApp', blank=True)
    
    # Настройки интернет-магазина
    default_currency = models.CharField('Валюта по умолчанию', max_length=10, default='RUB')
    tax_rate = models.DecimalField('Налоговая ставка (%)', max_digits=5, decimal_places=2, default=20.00)
    min_free_delivery_amount = models.DecimalField('Минимальная сумма для бесплатной доставки', max_digits=10, decimal_places=2, default=3000.00)
    delivery_cost = models.DecimalField('Стоимость доставки', max_digits=10, decimal_places=2, default=300.00)
    
    # Настройки бонусной системы
    bonus_rate = models.DecimalField('Бонусный процент (%)', max_digits=5, decimal_places=2, default=1.00)
    points_per_ruble = models.PositiveIntegerField('Баллов за рубль', default=1)
    
    # Настройки безопасности
    password_min_length = models.PositiveIntegerField('Минимальная длина пароля', default=8)
    require_phone_verification = models.BooleanField('Требуется подтверждение телефона', default=False)
    require_email_verification = models.BooleanField('Требуется подтверждение email', default=False)
    
    # Настройки SEO
    google_analytics_id = models.CharField('Google Analytics ID', max_length=20, blank=True)
    yandex_metrica_id = models.PositiveIntegerField('Яндекс.Метрика ID', null=True, blank=True)
    
    # Общие настройки
    maintenance_mode = models.BooleanField('Режим обслуживания', default=False)
    allow_user_registration = models.BooleanField('Разрешить регистрацию', default=True)
    allow_reviews = models.BooleanField('Разрешить отзывы', default=True)
    
    # Метаданные
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    
    class Meta:
        verbose_name = 'Настройки сайта'
        verbose_name_plural = 'Настройки сайта'
    
    def __str__(self):
        return 'Настройки сайта'
    
    @classmethod
    def get_settings(cls):
        """Получить настройки сайта (создать по умолчанию если не существуют)"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings


class Banner(models.Model):
    """
    Баннеры на главной странице
    """
    BANNER_TYPES = [
        ('main', 'Главный баннер'),
        ('promo', 'Промо-баннер'),
        ('category', 'Категорийный баннер'),
        ('product', 'Товарный баннер'),
    ]
    
    # Основная информация
    title = models.CharField('Заголовок', max_length=200)
    subtitle = models.CharField('Подзаголовок', max_length=300, blank=True)
    description = models.TextField('Описание', blank=True)
    image = models.ImageField('Изображение', upload_to='banners/')
    
    # Ссылка
    link_url = models.URLField('Ссылка', blank=True)
    link_text = models.CharField('Текст ссылки', max_length=50, blank=True)
    
    # Настройки отображения
    banner_type = models.CharField('Тип баннера', max_length=20, choices=BANNER_TYPES, default='main')
    is_active = models.BooleanField('Активен', default=True)
    sort_order = models.PositiveIntegerField('Порядок сортировки', default=0)
    
    # Связи
    category = models.ForeignKey('catalog.Category', on_delete=models.CASCADE, null=True, blank=True, related_name='banners')
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, null=True, blank=True, related_name='banners')
    
    # Период показа
    start_date = models.DateTimeField('Дата начала', null=True, blank=True)
    end_date = models.DateTimeField('Дата окончания', null=True, blank=True)
    
    # Метаданные
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    
    class Meta:
        verbose_name = 'Баннер'
        verbose_name_plural = 'Баннеры'
        ordering = ['sort_order', '-created_at']
    
    def __str__(self):
        return self.title
    
    def is_active_now(self):
        """Проверить, активен ли баннер в данный момент"""
        now = timezone.now()
        if not self.is_active:
            return False
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True


class Slider(models.Model):
    """
    Слайдер на главной странице
    """
    # Основная информация
    title = models.CharField('Заголовок', max_length=200)
    subtitle = models.CharField('Подзаголовок', max_length=300, blank=True)
    description = models.TextField('Описание', blank=True)
    image = models.ImageField('Изображение', upload_to='slider/')
    
    # Ссылка
    link_url = models.URLField('Ссылка', blank=True)
    link_text = models.CharField('Текст ссылки', max_length=50, blank=True)
    
    # Настройки отображения
    is_active = models.BooleanField('Активен', default=True)
    sort_order = models.PositiveIntegerField('Порядок сортировки', default=0)
    
    # Цвета текста
    text_color = models.CharField('Цвет текста', max_length=7, default='#ffffff', help_text='HEX код цвета')
    overlay_opacity = models.DecimalField('Непрозрачность наложения', max_digits=3, decimal_places=2, default=0.5, help_text='От 0.0 до 1.0')
    
    # Период показа
    start_date = models.DateTimeField('Дата начала', null=True, blank=True)
    end_date = models.DateTimeField('Дата окончания', null=True, blank=True)
    
    # Метаданные
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    
    class Meta:
        verbose_name = 'Слайд'
        verbose_name_plural = 'Слайдер'
        ordering = ['sort_order', '-created_at']
    
    def __str__(self):
        return self.title
    
    def is_active_now(self):
        """Проверить, активен ли слайд в данный момент"""
        now = timezone.now()
        if not self.is_active:
            return False
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True


class ContactForm(models.Model):
    """
    Сообщения с формы обратной связи
    """
    SUBJECT_CHOICES = [
        ('general', 'Общий вопрос'),
        ('order', 'Вопрос по заказу'),
        ('return', 'Возврат товара'),
        ('technical', 'Техническая поддержка'),
        ('partnership', 'Сотрудничество'),
        ('other', 'Другое'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'Новое'),
        ('in_progress', 'В обработке'),
        ('answered', 'Отвечено'),
        ('closed', 'Закрыто'),
    ]
    
    # Основная информация
    name = models.CharField('Имя', max_length=100)
    email = models.EmailField('Email')
    phone = models.CharField('Телефон', max_length=20, blank=True)
    subject = models.CharField('Тема', max_length=20, choices=SUBJECT_CHOICES)
    message = models.TextField('Сообщение')
    
    # Статус обработки
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='new')
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='assigned_contacts')
    
    # Ответ
    admin_response = models.TextField('Ответ администратора', blank=True)
    responded_at = models.DateTimeField('Отвечено', null=True, blank=True)
    responded_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='responded_contacts')
    
    # IP и User-Agent для борьбы со спамом
    ip_address = models.GenericIPAddressField('IP адрес', null=True, blank=True)
    user_agent = models.CharField('User Agent', max_length=500, blank=True)
    
    # Метаданные
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    
    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.subject}"


class SearchLog(models.Model):
    """
    Логи поиска для аналитики и улучшения поиска
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='searches')
    session_key = models.CharField('Ключ сессии', max_length=40, null=True, blank=True)
    
    # Поисковый запрос
    query = models.CharField('Поисковый запрос', max_length=200)
    filters = models.JSONField('Примененные фильтры', default=dict, blank=True)
    
    # Результаты поиска
    results_count = models.PositiveIntegerField('Количество результатов', default=0)
    clicked_product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, null=True, blank=True, related_name='found_through_search')
    
    # Метаданные
    searched_at = models.DateTimeField('Поиск выполнен', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Поисковый запрос'
        verbose_name_plural = 'Поисковые запросы'
        ordering = ['-searched_at']
        indexes = [
            models.Index(fields=['query']),
            models.Index(fields=['-searched_at']),
        ]
    
    def __str__(self):
        return f"{self.query} ({self.results_count} результатов)"


class Page(models.Model):
    """
    Статические страницы сайта
    """
    # Основная информация
    title = models.CharField('Заголовок', max_length=200)
    slug = models.SlugField('URL-идентификатор', max_length=200, unique=True)
    content = models.TextField('Содержимое')
    
    # SEO поля
    meta_title = models.CharField('Meta заголовок', max_length=60, blank=True)
    meta_description = models.CharField('Meta описание', max_length=160, blank=True)
    meta_keywords = models.CharField('Meta ключевые слова', max_length=200, blank=True)
    
    # Настройки отображения
    is_published = models.BooleanField('Опубликовано', default=True)
    show_in_menu = models.BooleanField('Показывать в меню', default=False)
    menu_order = models.PositiveIntegerField('Порядок в меню', default=0)
    
    # Метаданные
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена', auto_now=True)
    
    class Meta:
        verbose_name = 'Страница'
        verbose_name_plural = 'Страницы'
        ordering = ['menu_order', 'title']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.meta_title:
            self.meta_title = self.title
        super().save(*args, **kwargs)


class Notification(models.Model):
    """
    Уведомления для пользователей
    """
    TYPES = [
        ('order', 'Заказ'),
        ('payment', 'Платеж'),
        ('delivery', 'Доставка'),
        ('promotion', 'Акция'),
        ('system', 'Система'),
    ]
    
    # Основная информация
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField('Тип уведомления', max_length=20, choices=TYPES)
    title = models.CharField('Заголовок', max_length=200)
    message = models.TextField('Сообщение')
    
    # Связанный объект
    related_object_type = models.CharField('Тип связанного объекта', max_length=50, blank=True)
    related_object_id = models.PositiveIntegerField('ID связанного объекта', null=True, blank=True)
    
    # Настройки отображения
    is_read = models.BooleanField('Прочитано', default=False)
    is_sent_email = models.BooleanField('Отправлено на email', default=False)
    
    # Метаданные
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    read_at = models.DateTimeField('Прочитано', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.title}"
    
    def mark_as_read(self):
        """Отметить как прочитанное"""
        from django.utils import timezone
        self.is_read = True
        self.read_at = timezone.now()
        self.save()


class Feedback(models.Model):
    """
    Обратная связь и предложения
    """
    CATEGORIES = [
        ('bug', 'Ошибка'),
        ('feature', 'Новая функция'),
        ('improvement', 'Улучшение'),
        ('other', 'Другое'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'Новая'),
        ('reviewing', 'На рассмотрении'),
        ('accepted', 'Принята'),
        ('rejected', 'Отклонена'),
        ('implemented', 'Реализована'),
    ]
    
    # Основная информация
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedback', null=True, blank=True)
    category = models.CharField('Категория', max_length=20, choices=CATEGORIES)
    title = models.CharField('Заголовок', max_length=200)
    description = models.TextField('Описание')
    
    # Статус обработки
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='new')
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='assigned_feedback')
    
    # Ответ
    admin_response = models.TextField('Ответ администратора', blank=True)
    responded_at = models.DateTimeField('Отвечено', null=True, blank=True)
    responded_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='responded_feedback')
    
    # Метаданные
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    
    class Meta:
        verbose_name = 'Обратная связь'
        verbose_name_plural = 'Обратная связь'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.category}"
