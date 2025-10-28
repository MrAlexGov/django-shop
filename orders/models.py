"""
Модели заказов для интернет-магазина мобильных телефонов
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.urls import reverse
import uuid

from catalog.models import Product
from cart.models import Cart
from accounts.models import Address, DiscountCode

User = get_user_model()


class Order(models.Model):
    """
    Основная модель заказа
    """
    # Статусы заказа согласно ТЗ
    STATUS_CHOICES = [
        ('pending', 'Ожидает обработки'),
        ('processing', 'В обработке'),
        ('assembly', 'Сборка'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('completed', 'Выполнен'),
        ('cancelled', 'Отменен'),
        ('refunded', 'Возвращен'),
    ]
    
    # Типы заказа
    ORDER_TYPES = [
        ('standard', 'Стандартный'),
        ('express', 'Экспресс'),
        ('gift', 'Подарочный'),
        ('wholesale', 'Оптовый'),
    ]
    
    # Основная информация
    order_number = models.CharField('Номер заказа', max_length=20, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    
    # Статус и тип заказа
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='pending')
    order_type = models.CharField('Тип заказа', max_length=20, choices=ORDER_TYPES, default='standard')
    
    # Основные суммы
    subtotal = models.DecimalField('Сумма товаров', max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField('Скидка', max_digits=12, decimal_places=2, default=0)
    delivery_cost = models.DecimalField('Доставка', max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField('Налог', max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField('Общая сумма', max_digits=12, decimal_places=2, default=0)
    
    # Скидки
    applied_discount = models.ForeignKey(
        DiscountCode, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='orders',
        verbose_name='Примененная скидка'
    )
    bonus_points_used = models.PositiveIntegerField('Использовано бонусов', default=0)
    bonus_points_earned = models.PositiveIntegerField('Заработано бонусов', default=0)
    
    # Адреса
    billing_address = models.ForeignKey(
        Address, 
        on_delete=models.PROTECT, 
        related_name='billing_orders',
        verbose_name='Платежный адрес'
    )
    shipping_address = models.ForeignKey(
        Address, 
        on_delete=models.PROTECT, 
        related_name='shipping_orders',
        verbose_name='Адрес доставки'
    )
    
    # Информация о доставке
    delivery_method = models.CharField(
        'Способ доставки',
        max_length=50,
        choices=[
            ('courier', 'Курьерская доставка'),
            ('pickup', 'Самовывоз'),
            ('express', 'Экспресс доставка'),
            ('post', 'Почта России'),
        ]
    )
    
    delivery_date = models.DateField('Дата доставки', null=True, blank=True)
    delivery_time_slot = models.CharField(
        'Время доставки',
        max_length=20,
        choices=[
            ('', 'Любое'),
            ('09-12', '09:00 - 12:00'),
            ('12-15', '12:00 - 15:00'),
            ('15-18', '15:00 - 18:00'),
            ('18-21', '18:00 - 21:00'),
        ],
        blank=True
    )
    delivery_comment = models.TextField('Комментарий к доставке', blank=True)
    
    # Информация об оплате
    payment_method = models.CharField(
        'Способ оплаты',
        max_length=50,
        choices=[
            ('card', 'Банковская карта'),
            ('cash', 'Наличными при получении'),
            ('online', 'Онлайн оплата'),
            ('installments', 'Рассрочка'),
            ('bonus', 'Бонусными баллами'),
        ]
    )
    
    payment_status = models.CharField(
        'Статус оплаты',
        max_length=20,
        choices=[
            ('pending', 'Ожидает оплаты'),
            ('paid', 'Оплачен'),
            ('partial', 'Частично оплачен'),
            ('refunded', 'Возвращен'),
            ('failed', 'Ошибка оплаты'),
        ],
        default='pending'
    )
    
    payment_reference = models.CharField('Референс оплаты', max_length=100, blank=True)
    payment_date = models.DateTimeField('Дата оплаты', null=True, blank=True)
    
    # Дополнительная информация
    customer_note = models.TextField('Заметка клиента', blank=True)
    admin_note = models.TextField('Заметка администратора', blank=True)
    gift_message = models.TextField('Поздравительное сообщение', blank=True)
    gift_wrapping = models.BooleanField('Подарочная упаковка', default=False)
    
    # Временные метки
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    confirmed_at = models.DateTimeField('Подтвержден', null=True, blank=True)
    shipped_at = models.DateTimeField('Отправлен', null=True, blank=True)
    delivered_at = models.DateTimeField('Доставлен', null=True, blank=True)
    completed_at = models.DateTimeField('Завершен', null=True, blank=True)
    
    # Метаданные
    ip_address = models.GenericIPAddressField('IP адрес', null=True, blank=True)
    user_agent = models.TextField('User Agent', null=True, blank=True)
    source = models.CharField('Источник заказа', max_length=50, default='web')
    
    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Заказ #{self.order_number} от {self.user.get_full_name()}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        self.calculate_totals()
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """Генерация уникального номера заказа"""
        from django.utils import timezone
        timestamp = timezone.now().strftime('%Y%m%d')
        unique_id = str(uuid.uuid4()).split('-')[0].upper()
        return f"{timestamp}-{unique_id}"
    
    def calculate_totals(self):
        """Расчет общих сумм заказа"""
        if self.items.exists():
            self.subtotal = sum(item.total_price for item in self.items.filter(is_active=True))
            self.discount_amount = sum(item.discount_amount for item in self.items.filter(is_active=True))
            
            # Применяем скидку от промокода
            if self.applied_discount and self.applied_discount.is_valid():
                if self.applied_discount.discount_type == 'percentage':
                    discount = self.subtotal * (self.applied_discount.value / Decimal('100'))
                elif self.applied_discount.discount_type == 'fixed':
                    discount = min(self.applied_discount.value, self.subtotal)
                else:
                    discount = Decimal('0.00')
                self.discount_amount += discount
            else:
                self.applied_discount = None
            
            # Рассчитываем налог (примерно 20% НДС)
            self.tax_amount = (self.subtotal - self.discount_amount) * Decimal('0.20')
            
            # Итоговая сумма
            subtotal_after_discount = self.subtotal - self.discount_amount
            self.total_amount = subtotal_after_discount + self.delivery_cost + self.tax_amount - self.bonus_points_used
    
    def update_status(self, new_status, user=None):
        """Обновление статуса заказа"""
        old_status = self.status
        self.status = new_status
        
        # Обновляем временные метки в зависимости от статуса
        from django.utils import timezone
        if new_status == 'confirmed':
            self.confirmed_at = timezone.now()
        elif new_status == 'shipped':
            self.shipped_at = timezone.now()
        elif new_status == 'delivered':
            self.delivered_at = timezone.now()
        elif new_status == 'completed':
            self.completed_at = timezone.now()
            # Начисляем бонусные баллы при завершении заказа
            earned_points = int(self.total_amount // 100)  # 1 балл за каждые 100 рублей
            self.bonus_points_earned = earned_points
            if self.user:
                self.user.add_bonus_points(earned_points)
        
        self.save()
        
        # Отправляем уведомления об изменении статуса
        self.send_status_notification(old_status, new_status, user)
    
    def send_status_notification(self, old_status, new_status, user=None):
        """Отправка уведомления об изменении статуса"""
        try:
            # Импортируем здесь, чтобы избежать циклических импортов
            from core.notification_system import notify_order_status_change
            notify_order_status_change(self, old_status, new_status, user)
        except ImportError:
            # Если система уведомлений недоступна, логируем в консоль
            print(f"Уведомление: Заказ {self.order_number} изменен с '{old_status}' на '{new_status}'")
    
    def can_cancel(self):
        """Проверка возможности отмены заказа"""
        return self.status in ['pending', 'processing']
    
    def can_edit(self):
        """Проверка возможности редактирования заказа"""
        return self.status in ['pending', 'processing']
    
    def can_return(self):
        """Проверка возможности возврата"""
        return self.status in ['delivered', 'completed']
    
    def get_absolute_url(self):
        return reverse('orders:order_detail', kwargs={'order_number': self.order_number})
    
    @property
    def is_paid(self):
        return self.payment_status == 'paid'
    
    @property
    def is_delivered(self):
        return self.status in ['delivered', 'completed']
    
    @property
    def days_since_order(self):
        from django.utils import timezone
        return (timezone.now() - self.created_at).days


class OrderItem(models.Model):
    """
    Товар в заказе
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    
    # Основные поля
    quantity = models.PositiveIntegerField('Количество')
    unit_price = models.DecimalField('Цена за единицу', max_digits=10, decimal_places=2)
    total_price = models.DecimalField('Общая стоимость', max_digits=12, decimal_places=2, default=0)
    
    # Скидки на товар
    old_unit_price = models.DecimalField('Старая цена', max_digits=10, decimal_places=2, null=True, blank=True)
    discount_percent = models.DecimalField('Процент скидки', max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField('Размер скидки', max_digits=12, decimal_places=2, default=0)
    
    # Кэшированные данные товара
    product_name = models.CharField('Название товара', max_length=200)
    product_sku = models.CharField('Артикул', max_length=50)
    product_brand = models.CharField('Бренд', max_length=100)
    
    # Дополнительная информация
    warranty_months = models.PositiveIntegerField('Гарантия (месяцев)', default=12)
    serial_numbers = models.TextField('Серийные номера', blank=True)
    
    # Статус товара в заказе
    is_active = models.BooleanField('Активен', default=True)
    is_returned = models.BooleanField('Возвращен', default=False)
    return_reason = models.TextField('Причина возврата', blank=True)
    
    # Метаданные
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    
    class Meta:
        verbose_name = 'Товар в заказе'
        verbose_name_plural = 'Товары в заказе'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product_name} x{self.quantity} (Заказ #{self.order.order_number})"
    
    def save(self, *args, **kwargs):
        # Кэшируем данные товара
        if not self.product_name:
            self.product_name = self.product.name
            self.product_sku = self.product.sku
            self.product_brand = self.product.brand.name
            self.warranty_months = self.product.warranty_months
        
        # Рассчитываем цены
        base_total = self.quantity * self.unit_price
        
        # Скидка на товар
        if self.product.old_price and self.product.old_price > self.product.price:
            self.old_unit_price = self.product.old_price
            unit_discount = self.product.old_price - self.product.price
            self.discount_percent = (unit_discount / self.product.old_price * 100).quantize(Decimal('0.01'))
            self.discount_amount = self.quantity * unit_discount
        else:
            self.discount_amount = Decimal('0.00')
            self.discount_percent = Decimal('0.00')
        
        # Итоговая стоимость
        self.total_price = base_total - self.discount_amount
        
        super().save(*args, **kwargs)


class OrderHistory(models.Model):
    """
    История изменений заказа
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='history')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_history')
    
    # Информация об изменении
    action = models.CharField('Действие', max_length=100)
    old_status = models.CharField('Предыдущий статус', max_length=20, blank=True)
    new_status = models.CharField('Новый статус', max_length=20, blank=True)
    comment = models.TextField('Комментарий', blank=True)
    
    # Метаданные
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    ip_address = models.GenericIPAddressField('IP адрес', null=True, blank=True)
    
    class Meta:
        verbose_name = 'История заказа'
        verbose_name_plural = 'История заказов'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.order.order_number} - {self.action}"


class Payment(models.Model):
    """
    Платежи по заказам
    """
    PAYMENT_METHODS = [
        ('card', 'Банковская карта'),
        ('cash', 'Наличные'),
        ('bank_transfer', 'Банковский перевод'),
        ('online', 'Онлайн платеж'),
        ('crypto', 'Криптовалюта'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Ожидает'),
        ('processing', 'В обработке'),
        ('completed', 'Завершен'),
        ('failed', 'Ошибка'),
        ('cancelled', 'Отменен'),
        ('refunded', 'Возвращен'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    payment_method = models.CharField('Способ оплаты', max_length=20, choices=PAYMENT_METHODS)
    amount = models.DecimalField('Сумма', max_digits=12, decimal_places=2)
    currency = models.CharField('Валюта', max_length=3, default='RUB')
    status = models.CharField('Статус', max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # Информация о платеже
    transaction_id = models.CharField('ID транзакции', max_length=100, blank=True)
    payment_gateway = models.CharField('Платежная система', max_length=50, blank=True)
    gateway_response = models.JSONField('Ответ платежной системы', default=dict)
    
    # Временные метки
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    processed_at = models.DateTimeField('Обработан', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Платеж {self.amount} по заказу {self.order.order_number}"


class Shipment(models.Model):
    """
    Доставка заказов
    """
    SHIPMENT_STATUS = [
        ('pending', 'Ожидает отправки'),
        ('in_transit', 'В пути'),
        ('delivered', 'Доставлен'),
        ('failed', 'Не удалось доставить'),
        ('returned', 'Возвращен'),
    ]
    
    DELIVERY_METHODS = [
        ('courier', 'Курьер'),
        ('pickup', 'Самовывоз'),
        ('post', 'Почта'),
        ('express', 'Экспресс'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='shipments')
    method = models.CharField('Способ доставки', max_length=20, choices=DELIVERY_METHODS)
    status = models.CharField('Статус', max_length=20, choices=SHIPMENT_STATUS, default='pending')
    
    # Информация о доставке
    carrier = models.CharField('Перевозчик', max_length=100, blank=True)
    tracking_number = models.CharField('Трек-номер', max_length=100, blank=True)
    delivery_address = models.TextField('Адрес доставки')
    
    # Даты
    shipped_at = models.DateTimeField('Отправлен', null=True, blank=True)
    delivered_at = models.DateTimeField('Доставлен', null=True, blank=True)
    estimated_delivery = models.DateField('Плановая доставка', null=True, blank=True)
    
    # Комментарии
    delivery_comment = models.TextField('Комментарий доставки', blank=True)
    recipient_signature = models.CharField('Подпись получателя', max_length=200, blank=True)
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Доставка'
        verbose_name_plural = 'Доставки'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Доставка заказа {self.order.order_number}"


class OrderReturn(models.Model):
    """
    Возвраты товаров
    """
    RETURN_REASONS = [
        ('defective', 'Товар неисправен'),
        ('wrong_item', 'Неправильный товар'),
        ('damaged', 'Поврежден при доставке'),
        ('not_as_described', 'Не соответствует описанию'),
        ('changed_mind', 'Передумал'),
        ('other', 'Другое'),
    ]
    
    RETURN_STATUS = [
        ('requested', 'Запрошен'),
        ('approved', 'Одобрен'),
        ('rejected', 'Отклонен'),
        ('received', 'Получен'),
        ('refunded', 'Возвращен'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='returns')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='returns')
    
    reason = models.CharField('Причина возврата', max_length=20, choices=RETURN_REASONS)
    reason_text = models.TextField('Подробное описание причины')
    status = models.CharField('Статус', max_length=20, choices=RETURN_STATUS, default='requested')
    
    # Информация о возврате
    quantity = models.PositiveIntegerField('Количество')
    refund_amount = models.DecimalField('Сумма возврата', max_digits=12, decimal_places=2)
    
    # Данные клиента
    customer_note = models.TextField('Заметка клиента', blank=True)
    admin_note = models.TextField('Заметка администратора', blank=True)
    
    # Временные метки
    requested_at = models.DateTimeField('Запрошен', auto_now_add=True)
    processed_at = models.DateTimeField('Обработан', null=True, blank=True)
    refunded_at = models.DateTimeField('Возвращен', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Возврат'
        verbose_name_plural = 'Возвраты'
        ordering = ['-requested_at']
    
    def __str__(self):
        return f"Возврат {self.order_item.product_name} по заказу {self.order.order_number}"


class OrderNotification(models.Model):
    """
    Уведомления по заказам
    """
    NOTIFICATION_TYPES = [
        ('order_created', 'Заказ создан'),
        ('order_confirmed', 'Заказ подтвержден'),
        ('order_shipped', 'Заказ отправлен'),
        ('order_delivered', 'Заказ доставлен'),
        ('order_completed', 'Заказ завершен'),
        ('order_cancelled', 'Заказ отменен'),
        ('payment_received', 'Платеж получен'),
        ('return_requested', 'Запрос возврата'),
    ]
    
    NOTIFICATION_CHANNELS = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push уведомление'),
        ('telegram', 'Telegram'),
        ('whatsapp', 'WhatsApp'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField('Тип уведомления', max_length=20, choices=NOTIFICATION_TYPES)
    channel = models.CharField('Канал', max_length=10, choices=NOTIFICATION_CHANNELS)
    
    # Содержимое уведомления
    subject = models.CharField('Тема', max_length=200, blank=True)
    message = models.TextField('Сообщение')
    
    # Статус отправки
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=[
            ('pending', 'Ожидает отправки'),
            ('sent', 'Отправлено'),
            ('delivered', 'Доставлено'),
            ('failed', 'Ошибка'),
        ],
        default='pending'
    )
    
    # Метаданные
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    sent_at = models.DateTimeField('Отправлено', null=True, blank=True)
    external_id = models.CharField('Внешний ID', max_length=100, blank=True)
    
    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_notification_type_display()} для заказа {self.order.order_number}"


class OrderAnalytics(models.Model):
    """
    Аналитика заказов
    """
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='analytics')
    
    # Аналитические данные
    conversion_source = models.CharField('Источник конверсии', max_length=100, blank=True)
    campaign_id = models.CharField('ID кампании', max_length=100, blank=True)
    referrer = models.URLField('Источник трафика', blank=True)
    landing_page = models.URLField('Лендинг страница', blank=True)
    
    # Браузер и устройство
    browser = models.CharField('Браузер', max_length=50, blank=True)
    os = models.CharField('Операционная система', max_length=50, blank=True)
    device_type = models.CharField('Тип устройства', max_length=20, blank=True)
    
    # Время выполнения операций
    time_to_checkout = models.PositiveIntegerField('Время до оформления (сек)', default=0)
    time_to_payment = models.PositiveIntegerField('Время до оплаты (сек)', default=0)
    time_to_ship = models.PositiveIntegerField('Время до отправки (сек)', default=0)
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Аналитика заказа'
        verbose_name_plural = 'Аналитика заказов'
    
    def __str__(self):
        return f"Аналитика заказа {self.order.order_number}"
