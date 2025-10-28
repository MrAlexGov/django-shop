"""
Модели корзины покупок для интернет-магазина мобильных телефонов
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from decimal import Decimal
import json

from catalog.models import Product
from accounts.models import DiscountCode

User = get_user_model()


class Cart(models.Model):
    """
    Модель корзины покупок
    """
    # Идентификация корзины
    session_key = models.CharField('ID сессии', max_length=40, null=True, blank=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='carts')
    
    # Основная информация
    is_active = models.BooleanField('Активна', default=True)
    is_completed = models.BooleanField('Завершена', default=False)
    items_count = models.PositiveIntegerField('Количество товаров', default=0)
    discount_code = models.CharField('Код скидки', max_length=50, blank=True, default='')
    
    # Суммы и цены
    subtotal = models.DecimalField('Подытог', max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField('Налог', max_digits=12, decimal_places=2, default=0)
    shipping_cost = models.DecimalField('Стоимость доставки (старое поле)', max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField('Общая сумма (старое поле)', max_digits=12, decimal_places=2, default=0)
    used_bonus_points = models.PositiveIntegerField('Использовано бонусных баллов', default=0)
    
    # Современные поля
    total_quantity = models.PositiveIntegerField('Общее количество', default=0)
    total_price = models.DecimalField('Общая стоимость', max_digits=12, decimal_places=2, default=0)
    total_discount = models.DecimalField('Общая скидка', max_digits=12, decimal_places=2, default=0)
    final_price = models.DecimalField('Итоговая стоимость', max_digits=12, decimal_places=2, default=0)
    
    # Скидки и промокоды
    applied_discount = models.ForeignKey(
        DiscountCode, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='carts',
        verbose_name='Примененная скидка'
    )
    discount_amount = models.DecimalField('Размер скидки', max_digits=10, decimal_places=2, default=0)
    
    # Доставка
    delivery_cost = models.DecimalField('Стоимость доставки', max_digits=10, decimal_places=2, default=0)
    free_delivery_threshold = models.DecimalField('Порог бесплатной доставки', max_digits=10, decimal_places=2, default=3000)
    
    # Метаданные
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена', auto_now=True)
    last_activity = models.DateTimeField('Последняя активность', auto_now=True)
    
    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'
        ordering = ['-last_activity']
    
    def __str__(self):
        if self.user:
            return f"Корзина пользователя {self.user.get_full_name()}"
        else:
            return f"Корзина сессии {self.session_key}"
    
    def save(self, *args, **kwargs):
        # Автоматический расчет количества и стоимости только для существующих корзин
        if self.pk:  # Только если объект уже сохранен в базе данных
            self.calculate_totals()
        super().save(*args, **kwargs)
    
    def calculate_totals(self):
        """Расчет общих сумм корзины"""
        if not self.items.exists():
            self.items_count = 0
            self.total_quantity = 0
            self.total_price = Decimal('0.00')
            self.total_discount = Decimal('0.00')
            self.final_price = Decimal('0.00')
            return
        
        # Подсчитываем количество товаров и общую стоимость
        items = self.items.filter(is_active=True)
        self.items_count = items.count()
        self.total_quantity = sum(item.quantity for item in items)
        
        # Общая стоимость (до скидок)
        self.total_price = sum(item.total_price for item in items)
        
        # Общая скидка
        self.total_discount = sum(item.discount_amount for item in items)
        
        # Применяем скидку от промокода
        if self.applied_discount and self.applied_discount.is_valid():
            discount_amount = self.applied_discount_amount()
            self.discount_amount = discount_amount
        else:
            self.applied_discount = None
            self.discount_amount = Decimal('0.00')
        
        # Итоговая стоимость
        subtotal = self.total_price - self.total_discount - self.discount_amount
        
        # Стоимость доставки
        self.delivery_cost = self.calculate_delivery_cost(subtotal)
        
        # Финальная стоимость
        self.final_price = subtotal + self.delivery_cost
    
    def calculate_delivery_cost(self, subtotal):
        """Расчет стоимости доставки"""
        if subtotal >= self.free_delivery_threshold or subtotal == 0:
            return Decimal('0.00')
        
        # Базовую стоимость доставки можно сделать настраиваемой
        return Decimal('299.00')
    
    def applied_discount_amount(self):
        """Расчет размера скидки от промокода"""
        if not self.applied_discount or not self.applied_discount.is_valid():
            return Decimal('0.00')
        
        discount = self.applied_discount
        subtotal = self.total_price - self.total_discount
        
        if discount.discount_type == 'percentage':
            return subtotal * (discount.value / Decimal('100'))
        elif discount.discount_type == 'fixed':
            return min(discount.value, subtotal)
        else:
            return Decimal('0.00')
    
    def add_item(self, product, quantity=1, price_override=None):
        """Добавление товара в корзину"""
        if not product.is_available:
            raise ValidationError('Товар недоступен для заказа')
        
        if quantity <= 0:
            raise ValidationError('Количество должно быть больше нуля')
        
        if product.stock_quantity < quantity:
            raise ValidationError('Недостаточно товара на складе')
        
        # Ищем существующий товар в корзине
        cart_item, created = CartItem.objects.get_or_create(
            cart=self,
            product=product,
            defaults={
                'quantity': quantity,
                'unit_price': price_override or product.price,
            }
        )
        
        if not created:
            # Обновляем количество существующего товара
            new_quantity = cart_item.quantity + quantity
            if product.stock_quantity < new_quantity:
                raise ValidationError('Недостаточно товара на складе')
            cart_item.quantity = new_quantity
        
        cart_item.save()
        self.save()
        return cart_item
    
    def update_item_quantity(self, product, new_quantity):
        """Обновление количества товара в корзине"""
        try:
            cart_item = self.items.get(product=product)
            
            if new_quantity <= 0:
                cart_item.delete()
            else:
                if product.stock_quantity < new_quantity:
                    raise ValidationError('Недостаточно товара на складе')
                cart_item.quantity = new_quantity
                cart_item.save()
            
            self.save()
            return True
        except CartItem.DoesNotExist:
            return False
    
    def remove_item(self, product):
        """Удаление товара из корзины"""
        try:
            cart_item = self.items.get(product=product)
            cart_item.delete()
            self.save()
            return True
        except CartItem.DoesNotExist:
            return False
    
    def clear(self):
        """Очистка корзины"""
        self.items.all().delete()
        self.applied_discount = None
        self.discount_amount = Decimal('0.00')
        self.save()
    
    def apply_discount_code(self, discount_code):
        """Применение промокода"""
        if not discount_code.is_valid():
            raise ValidationError('Промокод недействителен или истек')
        
        # Проверяем минимальную сумму заказа
        if discount_code.min_order_amount and self.total_price < discount_code.min_order_amount:
            raise ValidationError(f'Минимальная сумма заказа для этого промокода: {discount_code.min_order_amount}')
        
        # Проверяем максимальное количество использований
        if discount_code.max_uses and discount_code.current_uses >= discount_code.max_uses:
            raise ValidationError('Промокод больше недоступен')
        
        self.applied_discount = discount_code
        self.save()
        return True
    
    def remove_discount_code(self):
        """Удаление промокода"""
        self.applied_discount = None
        self.discount_amount = Decimal('0.00')
        self.save()
    
    def is_empty(self):
        """Проверка, пуста ли корзина"""
        return not self.items.filter(is_active=True).exists()
    
    def get_delivery_info(self):
        """Информация о доставке"""
        subtotal = self.total_price - self.total_discount - self.discount_amount
        
        if subtotal >= self.free_delivery_threshold:
            return {
                'cost': Decimal('0.00'),
                'is_free': True,
                'threshold': self.free_delivery_threshold,
                'needed': Decimal('0.00')
            }
        else:
            needed = self.free_delivery_threshold - subtotal
            return {
                'cost': self.calculate_delivery_cost(subtotal),
                'is_free': False,
                'threshold': self.free_delivery_threshold,
                'needed': needed
            }
    
    def get_summary(self):
        """Краткая информация о корзине"""
        return {
            'items_count': self.items_count,
            'total_quantity': self.total_quantity,
            'subtotal': self.total_price,
            'discount': self.total_discount + self.discount_amount,
            'delivery': self.delivery_cost,
            'total': self.final_price,
            'has_discount': bool(self.applied_discount),
            'delivery_info': self.get_delivery_info(),
        }


class CartItem(models.Model):
    """
    Товар в корзине
    """
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    
    # Основные поля
    quantity = models.PositiveIntegerField('Количество', default=1)
    unit_price = models.DecimalField('Цена за единицу', max_digits=10, decimal_places=2)
    total_price = models.DecimalField('Общая стоимость', max_digits=12, decimal_places=2, default=0)
    
    # Скидки
    old_unit_price = models.DecimalField('Старая цена', max_digits=10, decimal_places=2, null=True, blank=True)
    discount_percent = models.DecimalField('Процент скидки', max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField('Размер скидки', max_digits=12, decimal_places=2, default=0)
    
    # Дополнительные данные
    added_at = models.DateTimeField('Добавлен', auto_now_add=True)
    is_active = models.BooleanField('Активен', default=True)
    
    # Кэшированные данные товара (на случай изменения товара)
    product_name = models.CharField('Название товара', max_length=200)
    product_sku = models.CharField('Артикул', max_length=50)
    product_brand = models.CharField('Бренд', max_length=100, default='')
    
    class Meta:
        verbose_name = 'Товар в корзине'
        verbose_name_plural = 'Товары в корзине'
        ordering = ['-added_at']
        unique_together = ('cart', 'product')
    
    def __str__(self):
        return f"{self.product_name} x{self.quantity}"
    
    def save(self, *args, **kwargs):
        # Кэшируем данные товара
        if not self.product_name:
            self.product_name = self.product.name
            self.product_sku = self.product.sku
            self.product_brand = self.product.brand.name
        
        # Рассчитываем цену и скидку
        self.calculate_prices()
        super().save(*args, **kwargs)
    
    def calculate_prices(self):
        """Расчет цен и скидок"""
        # Базовая стоимость
        base_total = self.quantity * self.unit_price
        
        # Проверяем актуальность цен товара
        if self.product.price != self.unit_price:
            self.unit_price = self.product.price
            base_total = self.quantity * self.unit_price
        
        # Рассчитываем скидку
        if self.product.old_price and self.product.old_price > self.product.price:
            self.old_unit_price = self.product.old_price
            
            # Процентная скидка на единицу
            unit_discount = self.product.old_price - self.product.price
            self.discount_percent = (unit_discount / self.product.old_price * 100).quantize(Decimal('0.01'))
            
            # Общая скидка
            self.discount_amount = self.quantity * unit_discount
        else:
            self.discount_amount = Decimal('0.00')
            self.discount_percent = Decimal('0.00')
        
        # Итоговая стоимость
        self.total_price = base_total - self.discount_amount
    
    def update_quantity(self, new_quantity):
        """Обновление количества"""
        if new_quantity <= 0:
            self.delete()
            return
        
        if self.product.stock_quantity < new_quantity:
            raise ValidationError('Недостаточно товара на складе')
        
        self.quantity = new_quantity
        self.save()
    
    def get_discount_info(self):
        """Информация о скидке на товар"""
        if not self.discount_amount:
            return None
        
        return {
            'old_price': self.old_unit_price,
            'new_price': self.unit_price,
            'discount_percent': float(self.discount_percent),
            'discount_amount': float(self.discount_amount),
            'savings': float(self.discount_amount),
        }


class RecentlyViewed(models.Model):
    """
    Недавно просмотренные товары
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recently_viewed')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='in_recently_viewed')
    viewed_at = models.DateTimeField('Просмотрен', auto_now=True)
    
    class Meta:
        verbose_name = 'Недавно просмотренный'
        verbose_name_plural = 'Недавно просмотренные'
        ordering = ['-viewed_at']
        unique_together = ('user', 'product')
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.product.name}"


class CartSession(models.Model):
    """
    Информация о сессиях корзины
    """
    session_key = models.CharField('ID сессии', max_length=40, unique=True)
    cart = models.OneToOneField(Cart, on_delete=models.CASCADE, related_name='session')
    ip_address = models.GenericIPAddressField('IP адрес', null=True, blank=True)
    user_agent = models.TextField('User Agent', null=True, blank=True)
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    last_activity = models.DateTimeField('Последняя активность', auto_now=True)
    
    class Meta:
        verbose_name = 'Сессия корзины'
        verbose_name_plural = 'Сессии корзин'
    
    def __str__(self):
        return f"Сессия {self.session_key}"


class SavedForLater(models.Model):
    """
    Отложенные товары (на потом)
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='in_saved')
    quantity = models.PositiveIntegerField('Количество', default=1)
    unit_price = models.DecimalField('Цена за единицу', max_digits=10, decimal_places=2)
    saved_at = models.DateTimeField('Сохранен', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Отложенный товар'
        verbose_name_plural = 'Отложенные товары'
        ordering = ['-saved_at']
        unique_together = ('user', 'product')
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.product.name}"
    
    def save(self, *args, **kwargs):
        # Сохраняем актуальную цену
        if not self.unit_price:
            self.unit_price = self.product.price
        super().save(*args, **kwargs)


class CartAnalytics(models.Model):
    """
    Аналитика корзины покупок
    """
    # Идентификация
    session_key = models.CharField('ID сессии', max_length=40, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='cart_analytics')
    
    # Данные корзины
    cart_data = models.JSONField('Данные корзины')
    cart_value = models.DecimalField('Стоимость корзины', max_digits=12, decimal_places=2)
    items_count = models.PositiveIntegerField('Количество товаров')
    
    # Аналитика
    conversion_stage = models.CharField(
        'Этап конверсии',
        max_length=50,
        choices=[
            ('viewed', 'Просмотрена'),
            ('added_item', 'Добавлен товар'),
            ('started_checkout', 'Начато оформление'),
            ('completed_checkout', 'Завершено оформление'),
            ('abandoned', 'Покинута'),
        ]
    )
    
    # Временные метки
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена', auto_now=True)
    
    class Meta:
        verbose_name = 'Аналитика корзины'
        verbose_name_plural = 'Аналитика корзин'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Аналитика сессии {self.session_key}"


class CartAbandonment(models.Model):
    """
    Отслеживание покинутых корзин
    """
    cart = models.OneToOneField(Cart, on_delete=models.CASCADE, related_name='abandonment')
    abandonment_reason = models.CharField('Причина отказа', max_length=100, blank=True)
    abandoned_at = models.DateTimeField('Покинута', auto_now_add=True)
    
    # Данные пользователя на момент ухода
    email = models.EmailField('Email', null=True, blank=True)
    phone = models.CharField('Телефон', max_length=20, null=True, blank=True)
    
    # Статус возврата
    recovery_sent = models.BooleanField('Отправлено письмо возврата', default=False)
    recovery_opened = models.BooleanField('Открыто письмо возврата', default=False)
    recovered = models.BooleanField('Восстановлена', default=False)
    recovered_at = models.DateTimeField('Восстановлена', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Покинутая корзина'
        verbose_name_plural = 'Покинутые корзины'
        ordering = ['-abandoned_at']
    
    def __str__(self):
        return f"Покинутая корзина {self.cart.id}"


class BulkCartAction(models.Model):
    """
    Массовые операции с корзиной
    """
    ACTION_TYPES = [
        ('clear', 'Очистка'),
        ('apply_discount', 'Применение скидки'),
        ('set_delivery', 'Установка доставки'),
        ('export', 'Экспорт'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bulk_cart_actions')
    action_type = models.CharField('Тип действия', max_length=20, choices=ACTION_TYPES)
    action_data = models.JSONField('Данные действия')
    status = models.CharField('Статус', max_length=20, default='pending')
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    completed_at = models.DateTimeField('Завершена', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Массовая операция'
        verbose_name_plural = 'Массовые операции'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.action_type}"
