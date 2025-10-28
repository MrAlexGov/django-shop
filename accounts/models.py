"""
Модели пользователей для интернет-магазина мобильных телефонов
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator


class User(AbstractUser):
    """
    Расширенная модель пользователя
    """
    phone_regex = RegexValidator(
        regex=r'^(\+7|8)?\s?\(?\d{3}\)?\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}$',
        message="Номер телефона должен быть в формате: +7 (XXX) XXX-XX-XX или 8 (XXX) XXX-XX-XX"
    )
    
    first_name = models.CharField('Имя', max_length=30, blank=False)
    last_name = models.CharField('Фамилия', max_length=30, blank=False)
    email = models.EmailField('Email', unique=True)
    phone = models.CharField('Телефон', validators=[phone_regex], max_length=20, blank=True)
    date_of_birth = models.DateField('Дата рождения', null=True, blank=True)
    
    # Настройки пользователя
    is_subscribed = models.BooleanField('Подписка на новости', default=False)
    preferred_language = models.CharField(
        'Предпочитаемый язык', 
        max_length=10, 
        choices=[
            ('ru', 'Русский'),
            ('en', 'English'),
        ], 
        default='ru'
    )
    
    # Бонусная система
    bonus_points = models.IntegerField('Бонусные баллы', default=0)
    total_spent = models.DecimalField('Всего потрачено', max_digits=10, decimal_places=2, default=0)
    
    # Метаданные
    created_at = models.DateTimeField('Дата регистрации', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def add_bonus_points(self, points):
        """Добавить бонусные баллы"""
        self.bonus_points += points
        self.save(update_fields=['bonus_points'])
    
    def spend_bonus_points(self, points):
        """Потратить бонусные баллы"""
        if self.bonus_points >= points:
            self.bonus_points -= points
            self.save(update_fields=['bonus_points'])
            return True
        return False


class UserProfile(models.Model):
    """
    Профиль пользователя с дополнительной информацией
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Основная информация
    avatar = models.ImageField('Аватар', upload_to='avatars/', null=True, blank=True)
    bio = models.TextField('О себе', max_length=500, blank=True)
    
    # Адрес
    country = models.CharField('Страна', max_length=100, default='Россия')
    city = models.CharField('Город', max_length=100, blank=True)
    address = models.CharField('Адрес', max_length=200, blank=True)
    postal_code = models.CharField('Почтовый индекс', max_length=10, blank=True)
    
    # Настройки уведомлений
    email_notifications = models.BooleanField('Email уведомления', default=True)
    sms_notifications = models.BooleanField('SMS уведомления', default=False)
    push_notifications = models.BooleanField('Push уведомления', default=True)
    
    # Настройки покупок
    preferred_payment_method = models.CharField(
        'Предпочитаемый способ оплаты',
        max_length=50,
        choices=[
            ('card', 'Банковская карта'),
            ('cash', 'Наличные'),
            ('bonus', 'Бонусные баллы'),
        ],
        default='card'
    )
    
    # Метаданные
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    
    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'
    
    def __str__(self):
        return f"Профиль {self.user.get_full_name()}"


class Address(models.Model):
    """
    Адреса доставки пользователя
    """
    DELIVERY_TYPES = [
        ('home', 'Дом'),
        ('work', 'Работа'),
        ('other', 'Другой'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    type = models.CharField('Тип адреса', max_length=10, choices=DELIVERY_TYPES, default='home')
    
    # Адресные данные
    full_name = models.CharField('Полное имя получателя', max_length=100)
    phone = models.CharField('Телефон', max_length=20)
    country = models.CharField('Страна', max_length=100)
    city = models.CharField('Город', max_length=100)
    street = models.CharField('Улица', max_length=100)
    house = models.CharField('Дом', max_length=10)
    apartment = models.CharField('Квартира', max_length=10, blank=True)
    postal_code = models.CharField('Почтовый индекс', max_length=10)
    
    # Дополнительная информация
    comment = models.TextField('Комментарий к адресу', blank=True)
    is_default = models.BooleanField('Адрес по умолчанию', default=False)
    
    # Метаданные
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    
    class Meta:
        verbose_name = 'Адрес'
        verbose_name_plural = 'Адреса'
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.city}, {self.street} {self.house}"


class Wishlist(models.Model):
    """
    Список желаний пользователя
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name='in_wishlists')
    created_at = models.DateTimeField('Добавлен', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные товары'
        unique_together = ('user', 'product')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.product.name}"


class CompareList(models.Model):
    """
    Список сравнения товаров
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='compare_list')
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name='in_compare_lists')
    created_at = models.DateTimeField('Добавлен', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Сравнение'
        verbose_name_plural = 'Списки сравнения'
        unique_together = ('user', 'product')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.product.name}"


class DiscountCode(models.Model):
    """
    Промокоды и скидки
    """
    DISCOUNT_TYPES = [
        ('percentage', 'Процентная'),
        ('fixed', 'Фиксированная'),
        ('shipping', 'Доставка'),
    ]
    
    code = models.CharField('Код', max_length=50, unique=True)
    description = models.CharField('Описание', max_length=200)
    discount_type = models.CharField('Тип скидки', max_length=20, choices=DISCOUNT_TYPES)
    value = models.DecimalField('Значение', max_digits=10, decimal_places=2)
    
    # Ограничения использования
    max_uses = models.IntegerField('Максимальное использование', null=True, blank=True)
    current_uses = models.IntegerField('Текущее использование', default=0)
    min_order_amount = models.DecimalField('Минимальная сумма заказа', max_digits=10, decimal_places=2, default=0)
    
    # Временные ограничения
    valid_from = models.DateTimeField('Действует с')
    valid_until = models.DateTimeField('Действует до')
    
    # Активность
    is_active = models.BooleanField('Активен', default=True)
    
    # Метаданные
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    
    class Meta:
        verbose_name = 'Промокод'
        verbose_name_plural = 'Промокоды'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code} ({self.description})"
    
    def is_valid(self):
        """Проверить, действителен ли промокод"""
        from django.utils import timezone
        now = timezone.now()
        return (
            self.is_active and
            self.valid_from <= now <= self.valid_until and
            (self.max_uses is None or self.current_uses < self.max_uses)
        )
    
    def use_code(self):
        """Использовать промокод"""
        if self.is_valid():
            self.current_uses += 1
            self.save(update_fields=['current_uses'])
            return True
        return False


class UserDiscount(models.Model):
    """
    История использования промокодов пользователем
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discount_history')
    discount = models.ForeignKey(DiscountCode, on_delete=models.CASCADE)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='discounts')
    discount_amount = models.DecimalField('Размер скидки', max_digits=10, decimal_places=2)
    used_at = models.DateTimeField('Использован', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Использованная скидка'
        verbose_name_plural = 'Использованные скидки'
        ordering = ['-used_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.discount.code} - {self.order.id}"
