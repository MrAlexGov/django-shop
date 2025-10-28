"""
Формы для приложения cart (корзина покупок)
"""

from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import Cart, CartItem, SavedForLater, BulkCartAction
from catalog.models import Product
from accounts.models import DiscountCode


class CartItemForm(forms.ModelForm):
    """
    Форма для изменения товара в корзине
    """
    quantity = forms.IntegerField(
        label='Количество',
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 99
        })
    )
    
    class Meta:
        model = CartItem
        fields = ('quantity',)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.product:
            self.fields['quantity'].widget.attrs['max'] = self.instance.product.stock_quantity
    
    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if self.instance.product and quantity > self.instance.product.stock_quantity:
            raise ValidationError(f'Максимальное количество: {self.instance.product.stock_quantity}')
        return quantity


class AddToCartForm(forms.Form):
    """
    Форма добавления товара в корзину
    """
    product_id = forms.IntegerField(widget=forms.HiddenInput())
    quantity = forms.IntegerField(
        label='Количество',
        min_value=1,
        max_value=99,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 99
        })
    )
    
    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if quantity <= 0:
            raise ValidationError('Количество должно быть больше нуля')
        return quantity
    
    def clean_product_id(self):
        product_id = self.cleaned_data['product_id']
        try:
            product = Product.objects.get(id=product_id, is_active=True)
            if not product.is_available:
                raise ValidationError('Товар недоступен для заказа')
            return product_id
        except Product.DoesNotExist:
            raise ValidationError('Товар не найден')


class DiscountCodeForm(forms.Form):
    """
    Форма применения промокода
    """
    discount_code = forms.CharField(
        label='Промокод',
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите промокод'
        })
    )
    
    def clean_discount_code(self):
        code = self.cleaned_data['discount_code'].strip().upper()
        if not code:
            raise ValidationError('Введите промокод')
        
        try:
            discount = DiscountCode.objects.get(code=code)
            if not discount.is_valid():
                raise ValidationError('Промокод недействителен или истек')
            return discount
        except DiscountCode.DoesNotExist:
            raise ValidationError('Промокод не найден')


class BulkCartUpdateForm(forms.Form):
    """
    Форма массового обновления корзины
    """
    updates = forms.JSONField(
        label='Обновления',
        widget=forms.HiddenInput(),
        help_text='JSON данные об обновлениях товаров'
    )
    
    def clean_updates(self):
        updates = self.cleaned_data.get('updates')
        if not updates:
            raise ValidationError('Не указаны товары для обновления')
        
        if not isinstance(updates, list):
            raise ValidationError('Неверный формат данных')
        
        validated_updates = []
        for update in updates:
            if not isinstance(update, dict):
                continue
            
            product_id = update.get('product_id')
            quantity = update.get('quantity')
            
            if not product_id or not quantity:
                continue
            
            try:
                product = Product.objects.get(id=product_id, is_active=True)
                quantity = int(quantity)
                if quantity < 0:
                    continue
                validated_updates.append({
                    'product_id': product_id,
                    'quantity': quantity,
                    'product': product
                })
            except (Product.DoesNotExist, ValueError):
                continue
        
        if not validated_updates:
            raise ValidationError('Не найдено валидных товаров для обновления')
        
        return validated_updates


class SavedForLaterForm(forms.Form):
    """
    Форма работы с отложенными товарами
    """
    product_id = forms.IntegerField(widget=forms.HiddenInput())
    quantity = forms.IntegerField(
        label='Количество',
        min_value=1,
        max_value=99,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 99
        })
    )
    action = forms.ChoiceField(
        label='Действие',
        choices=[
            ('save', 'Сохранить'),
            ('move', 'Переместить в корзину'),
            ('remove', 'Удалить'),
        ],
        widget=forms.HiddenInput()
    )
    
    def clean_product_id(self):
        product_id = self.cleaned_data['product_id']
        try:
            product = Product.objects.get(id=product_id, is_active=True)
            return product_id
        except Product.DoesNotExist:
            raise ValidationError('Товар не найден')
    
    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if quantity <= 0:
            raise ValidationError('Количество должно быть больше нуля')
        return quantity


class CartDeliveryForm(forms.Form):
    """
    Форма выбора доставки
    """
    DELIVERY_TYPES = [
        ('courier', 'Курьерская доставка'),
        ('pickup', 'Самовывоз'),
        ('express', 'Экспресс доставка'),
    ]
    
    delivery_type = forms.ChoiceField(
        label='Способ доставки',
        choices=DELIVERY_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    address_id = forms.IntegerField(
        label='Адрес доставки',
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    delivery_date = forms.DateField(
        label='Дата доставки',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    delivery_time = forms.ChoiceField(
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
    
    comment = forms.CharField(
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
            from accounts.models import Address
            self.fields['address_id'].queryset = Address.objects.filter(user=user)
            if self.fields['address_id'].queryset.exists():
                self.fields['address_id'].empty_label = 'Выберите адрес'
            else:
                self.fields['address_id'].widget = forms.HiddenInput()
    
    def clean(self):
        cleaned_data = super().clean()
        delivery_type = cleaned_data.get('delivery_type')
        address_id = cleaned_data.get('address_id')
        
        if delivery_type in ['courier', 'express'] and not address_id:
            raise ValidationError('Выберите адрес доставки')
        
        return cleaned_data


class CartPaymentForm(forms.Form):
    """
    Форма выбора способа оплаты
    """
    PAYMENT_TYPES = [
        ('card', 'Банковская карта'),
        ('cash', 'Наличными при получении'),
        ('online', 'Онлайн оплата'),
        ('installments', 'Рассрочка'),
        ('bonus', 'Бонусными баллами'),
    ]
    
    payment_type = forms.ChoiceField(
        label='Способ оплаты',
        choices=PAYMENT_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    use_bonus_points = forms.BooleanField(
        label='Использовать бонусные баллы',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    bonus_points_to_use = forms.IntegerField(
        label='Количество баллов',
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 0
        })
    )
    
    installments_count = forms.ChoiceField(
        label='Количество платежей',
        required=False,
        choices=[
            (3, '3 месяца'),
            (6, '6 месяцев'),
            (12, '12 месяцев'),
            (24, '24 месяца'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        bonus_balance = kwargs.pop('bonus_balance', 0)
        super().__init__(*args, **kwargs)
        
        if user and user.is_authenticated:
            self.fields['bonus_points_to_use'].widget.attrs['max'] = bonus_balance
            
            # Скрываем опции, недоступные пользователю
            if bonus_balance <= 0:
                self.fields['use_bonus_points'].widget = forms.HiddenInput()
                self.fields['bonus_points_to_use'].widget = forms.HiddenInput()
    
    def clean(self):
        cleaned_data = super().clean()
        payment_type = cleaned_data.get('payment_type')
        use_bonus = cleaned_data.get('use_bonus_points')
        bonus_points = cleaned_data.get('bonus_points_to_use', 0)
        
        if use_bonus and bonus_points <= 0:
            raise ValidationError('Укажите количество баллов для списания')
        
        if payment_type == 'installments' and not cleaned_data.get('installments_count'):
            raise ValidationError('Выберите количество платежей')
        
        return cleaned_data


class CartBulkActionForm(forms.ModelForm):
    """
    Форма массовых операций с корзиной
    """
    ACTION_TYPES = [
        ('clear', 'Очистить корзину'),
        ('apply_discount', 'Применить скидку'),
        ('update_quantities', 'Обновить количество'),
        ('remove_selected', 'Удалить выбранные'),
        ('move_to_saved', 'Переместить в сохраненные'),
    ]
    
    action_type = forms.ChoiceField(
        label='Действие',
        choices=ACTION_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    item_ids = forms.JSONField(
        label='ID товаров',
        required=False,
        help_text='JSON массив ID товаров для операции'
    )
    
    discount_code = forms.CharField(
        label='Промокод',
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        })
    )
    
    class Meta:
        model = BulkCartAction
        fields = ('action_type', 'item_ids', 'discount_code')
    
    def clean(self):
        cleaned_data = super().clean()
        action_type = cleaned_data.get('action_type')
        item_ids = cleaned_data.get('item_ids')
        discount_code = cleaned_data.get('discount_code')
        
        if action_type in ['update_quantities', 'remove_selected', 'move_to_saved']:
            if not item_ids:
                raise ValidationError('Выберите товары для операции')
        
        if action_type == 'apply_discount' and not discount_code:
            raise ValidationError('Введите промокод')
        
        return cleaned_data


class QuickAddToCartForm(forms.Form):
    """
    Форма быстрого добавления в корзину (для AJAX)
    """
    product_id = forms.IntegerField(widget=forms.HiddenInput())
    quantity = forms.IntegerField(
        min_value=1,
        max_value=99,
        initial=1,
        widget=forms.HiddenInput()
    )


class CartNoteForm(forms.Form):
    """
    Форма добавления заметки к корзине
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


class CartGiftOptionsForm(forms.Form):
    """
    Форма опций подарочной упаковки
    """
    gift_wrapping = forms.BooleanField(
        label='Подарочная упаковка',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    gift_message = forms.CharField(
        label='Поздравительное сообщение',
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Поздравительное сообщение...'
        })
    )
    
    recipient_name = forms.CharField(
        label='Имя получателя',
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя получателя подарка'
        })
    )


class CartEstimateForm(forms.Form):
    """
    Форма расчета стоимости доставки
    """
    city = forms.CharField(
        label='Город',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите город'
        })
    )
    
    postal_code = forms.CharField(
        label='Почтовый индекс',
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Почтовый индекс'
        })
    )


class CartComparisonForm(forms.Form):
    """
    Форма сравнения корзин (для A/B тестирования)
    """
    experiment_id = forms.CharField(
        label='ID эксперимента',
        max_length=50,
        widget=forms.HiddenInput()
    )
    
    variant = forms.CharField(
        label='Вариант',
        max_length=10,
        widget=forms.HiddenInput()
    )
    
    user_segment = forms.CharField(
        label='Сегмент пользователя',
        max_length=50,
        required=False,
        widget=forms.HiddenInput()
    )