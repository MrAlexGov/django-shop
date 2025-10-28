"""
Формы для приложения orders (заказы)
"""

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from datetime import date, timedelta
from decimal import Decimal
from .models import Order, OrderItem
from accounts.models import Address


class CheckoutStep1Form(forms.Form):
    """
    Форма первого шага оформления заказа - данные о доставке
    """
    DELIVERY_METHODS = [
        ('courier', 'Курьерская доставка'),
        ('pickup', 'Самовывоз'),
        ('express', 'Экспресс доставка'),
    ]
    
    address_id = forms.IntegerField(
        label='Адрес доставки',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        })
    )
    
    delivery_method = forms.ChoiceField(
        label='Способ доставки',
        choices=DELIVERY_METHODS,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    delivery_date = forms.DateField(
        label='Дата доставки',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': date.today().isoformat()
        })
    )
    
    delivery_time_slot = forms.ChoiceField(
        label='Время доставки',
        required=False,
        choices=[
            ('', 'Любое'),
            ('09-12', '09:00 - 12:00'),
            ('12-15', '12:00 - 15:00'),
            ('15-18', '15:00 - 18:00'),
            ('18-21', '18:00 - 21:00'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    delivery_comment = forms.CharField(
        label='Комментарий к доставке',
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Дополнительные пожелания по доставке...'
        })
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and user.is_authenticated:
            self.fields['address_id'].queryset = Address.objects.filter(user=user)
            if self.fields['address_id'].queryset.exists():
                self.fields['address_id'].empty_label = 'Выберите адрес доставки'
            else:
                # Если нет сохраненных адресов, показываем инструкцию
                self.fields['address_id'].widget = forms.HiddenInput()
        
        # Устанавливаем минимальную дату доставки
        tomorrow = date.today() + timedelta(days=1)
        self.fields['delivery_date'].widget.attrs['min'] = tomorrow.isoformat()
    
    def clean_address_id(self):
        address_id = self.cleaned_data['address_id']
        if not address_id:
            raise ValidationError('Необходимо выбрать адрес доставки')
        return address_id
    
    def clean_delivery_date(self):
        delivery_date = self.cleaned_data['delivery_date']
        min_date = date.today() + timedelta(days=1)  # Минимум завтра
        if delivery_date < min_date:
            raise ValidationError('Дата доставки должна быть не ранее завтра')
        return delivery_date


class CheckoutStep2Form(forms.Form):
    """
    Форма второго шага оформления заказа - способ оплаты
    """
    PAYMENT_METHODS = [
        ('card', 'Банковская карта'),
        ('cash', 'Наличными при получении'),
        ('online', 'Онлайн оплата'),
        ('installments', 'Рассрочка'),
        ('bonus', 'Бонусными баллами'),
    ]
    
    payment_method = forms.ChoiceField(
        label='Способ оплаты',
        choices=PAYMENT_METHODS,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    use_bonus_points = forms.BooleanField(
        label='Использовать бонусные баллы',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    bonus_points_to_use = forms.IntegerField(
        label='Количество баллов',
        required=False,
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 0
        })
    )
    
    installments_count = forms.ChoiceField(
        label='Количество платежей',
        required=False,
        choices=[
            ('', 'Выберите количество платежей'),
            (3, '3 месяца'),
            (6, '6 месяцев'),
            (12, '12 месяцев'),
            (24, '24 месяца'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    customer_note = forms.CharField(
        label='Заметка к заказу',
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Дополнительные пожелания к заказу...'
        })
    )
    
    gift_message = forms.CharField(
        label='Поздравительное сообщение',
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Поздравительное сообщение для получателя подарка...'
        })
    )
    
    gift_wrapping = forms.BooleanField(
        label='Подарочная упаковка (+300 руб.)',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        bonus_balance = kwargs.pop('bonus_balance', 0)
        super().__init__(*args, **kwargs)
        
        if user and user.is_authenticated:
            self.fields['bonus_points_to_use'].widget.attrs['max'] = bonus_balance
            
            # Скрываем опции, если нет бонусных баллов
            if bonus_balance <= 0:
                self.fields['use_bonus_points'].widget = forms.CheckboxInput(attrs={
                    'class': 'form-check-input',
                    'disabled': True
                })
                self.fields['bonus_points_to_use'].widget = forms.HiddenInput()
                self.initial['use_bonus_points'] = False
                self.initial['bonus_points_to_use'] = 0
    
    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        use_bonus = cleaned_data.get('use_bonus_points')
        bonus_points = cleaned_data.get('bonus_points_to_use', 0)
        installments_count = cleaned_data.get('installments_count')
        
        # Проверка использования бонусных баллов
        if use_bonus and bonus_points <= 0:
            raise ValidationError('Укажите количество баллов для списания')
        
        # Проверка рассрочки
        if payment_method == 'installments' and not installments_count:
            raise ValidationError('Выберите количество платежей для рассрочки')
        
        return cleaned_data


class CheckoutStep3Form(forms.Form):
    """
    Форма третьего шага оформления заказа - подтверждение
    """
    terms_accepted = forms.BooleanField(
        label='Я принимаю условия использования',
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'required': True
        })
    )
    
    privacy_accepted = forms.BooleanField(
        label='Я согласен с политикой конфиденциальности',
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'required': True
        })
    )
    
    newsletter_subscription = forms.BooleanField(
        label='Подписаться на новости и специальные предложения',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    sms_notifications = forms.BooleanField(
        label='Получать SMS уведомления о статусе заказа',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    final_confirmation = forms.BooleanField(
        label='Подтверждаю заказ',
        required=True,
        help_text='Нажимая эту кнопку, вы подтверждаете правильность всех данных и соглашаетесь с условиями оформления заказа.',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'required': True
        })
    )


class OrderSearchForm(forms.Form):
    """
    Форма поиска заказов
    """
    order_number = forms.CharField(
        label='Номер заказа',
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например: 20250115-ABC123'
        })
    )
    
    date_from = forms.DateField(
        label='Дата с',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        label='Дата по',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    status = forms.ChoiceField(
        label='Статус',
        required=False,
        choices=[('', 'Все статусы')] + Order.STATUS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    min_amount = forms.DecimalField(
        label='Минимальная сумма',
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': 0
        })
    )
    
    max_amount = forms.DecimalField(
        label='Максимальная сумма',
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': 0
        })
    )


class OrderReturnForm(forms.Form):
    """
    Форма запроса на возврат товара
    """
    RETURN_REASONS = [
        ('defective', 'Товар неисправен'),
        ('wrong_item', 'Неправильный товар'),
        ('damaged', 'Поврежден при доставке'),
        ('not_as_described', 'Не соответствует описанию'),
        ('changed_mind', 'Передумал'),
        ('other', 'Другое'),
    ]
    
    order_item_id = forms.IntegerField(widget=forms.HiddenInput())
    
    reason = forms.ChoiceField(
        label='Причина возврата',
        choices=RETURN_REASONS,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    reason_text = forms.CharField(
        label='Подробное описание причины',
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Опишите подробно причину возврата...'
        })
    )
    
    contact_method = forms.ChoiceField(
        label='Предпочтительный способ связи',
        choices=[
            ('email', 'Email'),
            ('phone', 'Телефон'),
            ('sms', 'SMS'),
        ],
        initial='email',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    def __init__(self, *args, **kwargs):
        order = kwargs.pop('order', None)
        super().__init__(*args, **kwargs)
        
        if order:
            # Фильтруем только товары, которые можно вернуть
            available_items = order.items.filter(is_active=True, is_returned=False)
            choices = [(item.id, f"{item.product_name} x{item.quantity}") for item in available_items]
            self.fields['order_item_id'] = forms.ChoiceField(
                label='Товар для возврата',
                choices=choices,
                widget=forms.Select(attrs={
                    'class': 'form-select'
                })
            )


class QuickOrderForm(forms.Form):
    """
    Форма быстрого заказа
    """
    product_id = forms.IntegerField(widget=forms.HiddenInput())
    quantity = forms.IntegerField(
        min_value=1,
        max_value=10,
        initial=1,
        widget=forms.HiddenInput()
    )
    
    customer_name = forms.CharField(
        label='Ваше имя',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваше имя'
        })
    )
    
    customer_phone = forms.CharField(
        label='Номер телефона',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (999) 123-45-67'
        })
    )
    
    customer_email = forms.EmailField(
        label='Email',
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com'
        })
    )
    
    delivery_address = forms.CharField(
        label='Адрес доставки',
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Укажите адрес доставки'
        })
    )
    
    delivery_comment = forms.CharField(
        label='Комментарий',
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Дополнительные пожелания'
        })
    )
    
    payment_method = forms.ChoiceField(
        label='Способ оплаты',
        choices=[
            ('cash', 'Наличными при получении'),
            ('card', 'Банковская карта'),
        ],
        initial='cash',
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )


class OrderNoteForm(forms.Form):
    """
    Форма добавления заметки к заказу
    """
    note = forms.CharField(
        label='Заметка',
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Добавьте заметку к заказу...'
        })
    )


class OrderFilterForm(forms.Form):
    """
    Форма фильтрации заказов
    """
    STATUS_CHOICES = [
        ('', 'Все заказы'),
        ('pending', 'Ожидает обработки'),
        ('processing', 'В обработке'),
        ('assembly', 'Сборка'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('completed', 'Выполнен'),
        ('cancelled', 'Отменен'),
    ]
    
    status = forms.ChoiceField(
        label='Статус',
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    period = forms.ChoiceField(
        label='Период',
        choices=[
            ('', 'Все время'),
            ('today', 'Сегодня'),
            ('week', 'Последняя неделя'),
            ('month', 'Последний месяц'),
            ('year', 'Последний год'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    sort_by = forms.ChoiceField(
        label='Сортировка',
        choices=[
            ('-created_at', 'По дате (новые первыми)'),
            ('created_at', 'По дате (старые первыми)'),
            ('-total_amount', 'По сумме (большие первыми)'),
            ('total_amount', 'По сумме (маленькие первыми)'),
        ],
        initial='-created_at',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )


class OrderStatusUpdateForm(forms.Form):
    """
    Форма обновления статуса заказа (для администраторов)
    """
    new_status = forms.ChoiceField(
        label='Новый статус',
        choices=Order.STATUS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    admin_note = forms.CharField(
        label='Заметка администратора',
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Комментарий об изменении статуса...'
        })
    )
    
    notify_customer = forms.BooleanField(
        label='Уведомить клиента',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )


class BulkOrderActionForm(forms.Form):
    """
    Форма массовых операций с заказами
    """
    ACTION_CHOICES = [
        ('export', 'Экспорт в Excel'),
        ('print_labels', 'Печать накладных'),
        ('send_notifications', 'Отправить уведомления'),
        ('update_status', 'Обновить статус'),
        ('archive', 'Архивировать'),
    ]
    
    action = forms.ChoiceField(
        label='Действие',
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    order_ids = forms.CharField(
        label='ID заказов',
        widget=forms.HiddenInput(),
        help_text='JSON массив ID заказов'
    )
    
    new_status = forms.ChoiceField(
        label='Новый статус',
        choices=Order.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    notification_message = forms.CharField(
        label='Текст уведомления',
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Текст для отправки клиентам...'
        })
    )


class DeliveryEstimateForm(forms.Form):
    """
    Форма расчета доставки
    """
    city = forms.CharField(
        label='Город',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите название города'
        })
    )
    
    delivery_type = forms.ChoiceField(
        label='Тип доставки',
        choices=[
            ('courier', 'Курьерская'),
            ('pickup', 'Самовывоз'),
            ('express', 'Экспресс'),
        ],
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )
    
    address_details = forms.CharField(
        label='Детали адреса',
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Район, улица, дом...'
        })
    )


class PaymentMethodForm(forms.Form):
    """
    Форма выбора способа оплаты
    """
    PAYMENT_CHOICES = [
        ('card', 'Банковская карта'),
        ('cash', 'Наличными'),
        ('online', 'Онлайн платеж'),
        ('installments', 'Рассрочка'),
        ('bonus', 'Бонусными баллами'),
    ]
    
    payment_method = forms.ChoiceField(
        label='Способ оплаты',
        choices=PAYMENT_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )
    
    card_number = forms.CharField(
        label='Номер карты',
        required=False,
        max_length=19,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '1234 5678 9012 3456'
        })
    )
    
    card_holder = forms.CharField(
        label='Держатель карты',
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'IVAN PETROV'
        })
    )
    
    use_bonus_points = forms.BooleanField(
        label='Использовать бонусные баллы',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )