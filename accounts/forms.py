"""
Формы для приложения accounts (пользователи и личный кабинет)
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from datetime import date
from .models import UserProfile, Address

User = get_user_model()


class RegistrationForm(UserCreationForm):
    """
    Форма регистрации пользователя
    """
    email = forms.EmailField(
        label='Email',
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com'
        })
    )
    
    first_name = forms.CharField(
        label='Имя',
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваше имя'
        })
    )
    
    last_name = forms.CharField(
        label='Фамилия',
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите вашу фамилию'
        })
    )
    
    phone = forms.CharField(
        label='Номер телефона',
        required=False,
        max_length=20,
        validators=[RegexValidator(
            regex=r'^(\+7|8)?\s?\(?\d{3}\)?\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}$',
            message="Номер телефона должен быть в формате: +7 (XXX) XXX-XX-XX или 8 (XXX) XXX-XX-XX"
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (999) 123-45-67'
        })
    )
    
    date_of_birth = forms.DateField(
        label='Дата рождения',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    is_subscribed = forms.BooleanField(
        label='Подписаться на новости',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
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
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Придумайте логин'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Добавляем CSS классы к стандартным полям
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Придумайте пароль'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Повторите пароль'
        })
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError('Пользователь с таким email уже существует')
        return email
    
    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise ValidationError('Пользователь с таким логином уже существует')
        return username


class ProfileUpdateForm(forms.ModelForm):
    """
    Форма обновления профиля пользователя
    """
    email = forms.EmailField(
        label='Email',
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control'
        })
    )
    
    phone = forms.CharField(
        label='Номер телефона',
        required=False,
        max_length=20,
        validators=[RegexValidator(
            regex=r'^(\+7|8)?\s?\(?\d{3}\)?\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}$',
            message="Номер телефона должен быть в формате: +7 (XXX) XXX-XX-XX или 8 (XXX) XXX-XX-XX"
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        })
    )
    
    date_of_birth = forms.DateField(
        label='Дата рождения',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    preferred_language = forms.ChoiceField(
        label='Предпочитаемый язык',
        choices=[
            ('ru', 'Русский'),
            ('en', 'English'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone', 'date_of_birth', 'preferred_language', 'is_subscribed')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_subscribed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        profile = kwargs.pop('profile', None)
        super().__init__(*args, **kwargs)
        self.profile = profile
        
        if self.instance and self.instance.email:
            # Для редактирования, проверяем уникальность email
            self.fields['email'].widget.attrs['readonly'] = False
    
    def save_profile(self):
        """Сохранение данных профиля"""
        if self.profile:
            self.profile.preferred_language = self.cleaned_data.get('preferred_language', 'ru')
            self.profile.is_subscribed = self.cleaned_data.get('is_subscribed', False)
            self.profile.save()
        return self.profile
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exclude(id=self.instance.id).exists():
            raise ValidationError('Пользователь с таким email уже существует')
        return email


class ProfileUpdateFormWithImage(ProfileUpdateForm):
    """
    Форма обновления профиля с изображением
    """
    avatar = forms.ImageField(
        label='Фото профиля',
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
    
    bio = forms.CharField(
        label='О себе',
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Расскажите о себе...'
        })
    )
    
    country = forms.CharField(
        label='Страна',
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Россия'
        })
    )
    
    city = forms.CharField(
        label='Город',
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Москва'
        })
    )
    
    preferred_payment_method = forms.ChoiceField(
        label='Предпочитаемый способ оплаты',
        required=False,
        choices=[
            ('card', 'Банковская карта'),
            ('cash', 'Наличные'),
            ('bonus', 'Бонусные баллы'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.profile:
            self.fields['bio'].initial = self.profile.bio
            self.fields['country'].initial = self.profile.country
            self.fields['city'].initial = self.profile.city
            self.fields['preferred_payment_method'].initial = self.profile.preferred_payment_method
    
    def save_profile(self):
        """Сохранение данных профиля с дополнительными полями"""
        if self.profile:
            self.profile.bio = self.cleaned_data.get('bio', '')
            self.profile.country = self.cleaned_data.get('country', 'Россия')
            self.profile.city = self.cleaned_data.get('city', '')
            self.profile.preferred_payment_method = self.cleaned_data.get('preferred_payment_method', 'card')
            
            # Обработка изображения аватара
            avatar = self.cleaned_data.get('avatar')
            if avatar:
                self.profile.avatar = avatar
            
            self.profile.save()
        return super().save_profile()


class AddressForm(forms.ModelForm):
    """
    Форма для работы с адресами
    """
    DELIVERY_TYPES = [
        ('home', 'Дом'),
        ('work', 'Работа'),
        ('other', 'Другой'),
    ]
    
    type = forms.ChoiceField(
        label='Тип адреса',
        choices=DELIVERY_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    full_name = forms.CharField(
        label='Полное имя получателя',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Иванов Иван Иванович'
        })
    )
    
    phone = forms.CharField(
        label='Телефон',
        max_length=20,
        validators=[RegexValidator(
            regex=r'^(\+7|8)?\s?\(?\d{3}\)?\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}$',
            message="Номер телефона должен быть в формате: +7 (XXX) XXX-XX-XX или 8 (XXX) XXX-XX-XX"
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (999) 123-45-67'
        })
    )
    
    country = forms.CharField(
        label='Страна',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Россия'
        })
    )
    
    city = forms.CharField(
        label='Город',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Москва'
        })
    )
    
    street = forms.CharField(
        label='Улица',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ул. Тверская'
        })
    )
    
    house = forms.CharField(
        label='Дом',
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '10'
        })
    )
    
    apartment = forms.CharField(
        label='Квартира',
        required=False,
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '123'
        })
    )
    
    postal_code = forms.CharField(
        label='Почтовый индекс',
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '123456'
        })
    )
    
    comment = forms.CharField(
        label='Комментарий к адресу',
        required=False,
        max_length=200,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Дополнительная информация о доставке...'
        })
    )
    
    is_default = forms.BooleanField(
        label='Адрес по умолчанию',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    class Meta:
        model = Address
        fields = ('type', 'full_name', 'phone', 'country', 'city', 'street', 'house', 'apartment', 'postal_code', 'comment', 'is_default')
    
    def save(self, commit=True):
        address = super().save(commit=False)
        
        # Если устанавливаем адрес по умолчанию
        if address.is_default and hasattr(address, 'user') and address.user:
            # Убираем флаг по умолчанию у других адресов
            Address.objects.filter(user=address.user).update(is_default=False)
            address.is_default = True
        
        if commit:
            address.save()
        
        return address


class QuickAddressForm(forms.ModelForm):
    """
    Быстрая форма добавления адреса
    """
    class Meta:
        model = Address
        fields = ('full_name', 'phone', 'city', 'street', 'house', 'apartment')
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Полное имя'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Телефон'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Город'}),
            'street': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Улица'}),
            'house': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Дом'}),
            'apartment': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Квартира'}),
        }


class ChangePasswordForm(PasswordChangeForm):
    """
    Форма смены пароля
    """
    old_password = forms.CharField(
        label='Текущий пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите текущий пароль'
        })
    )
    
    new_password1 = forms.CharField(
        label='Новый пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите новый пароль'
        })
    )
    
    new_password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Повторите новый пароль'
        })
    )


class NotificationSettingsForm(forms.ModelForm):
    """
    Форма настроек уведомлений
    """
    email_notifications = forms.BooleanField(
        label='Email уведомления',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    sms_notifications = forms.BooleanField(
        label='SMS уведомления',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    push_notifications = forms.BooleanField(
        label='Push уведомления',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    class Meta:
        model = UserProfile
        fields = ('email_notifications', 'sms_notifications', 'push_notifications')


class AccountSettingsForm(forms.ModelForm):
    """
    Форма настроек аккаунта
    """
    preferred_language = forms.ChoiceField(
        label='Предпочитаемый язык',
        choices=[
            ('ru', 'Русский'),
            ('en', 'English'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    preferred_payment_method = forms.ChoiceField(
        label='Предпочитаемый способ оплаты',
        choices=[
            ('card', 'Банковская карта'),
            ('cash', 'Наличные'),
            ('bonus', 'Бонусные баллы'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    class Meta:
        model = User
        fields = ('preferred_language',)


class WishlistForm(forms.Form):
    """
    Форма для работы с избранным
    """
    product_id = forms.IntegerField(widget=forms.HiddenInput())


class BonusSpendForm(forms.Form):
    """
    Форма для траты бонусных баллов
    """
    BONUS_ACTIONS = [
        ('discount_5', 'Скидка 5%'),
        ('discount_10', 'Скидка 10%'),
        ('discount_15', 'Скидка 15%'),
        ('free_delivery', 'Бесплатная доставка'),
        ('gift', 'Подарок'),
    ]
    
    action = forms.ChoiceField(
        label='Выберите действие',
        choices=BONUS_ACTIONS,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    bonus_points = forms.IntegerField(
        label='Количество баллов',
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1
        })
    )


class UserSearchForm(forms.Form):
    """
    Форма поиска пользователей (для администраторов)
    """
    search_query = forms.CharField(
        label='Поиск',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя, email или телефон'
        })
    )
    
    date_from = forms.DateField(
        label='Регистрация с',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        label='Регистрация по',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    is_active = forms.BooleanField(
        label='Только активные',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    has_orders = forms.BooleanField(
        label='Только с заказами',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )


class UserAnalyticsForm(forms.Form):
    """
    Форма для аналитики пользователей
    """
    PERIOD_CHOICES = [
        ('week', 'Последняя неделя'),
        ('month', 'Последний месяц'),
        ('quarter', 'Последний квартал'),
        ('year', 'Последний год'),
        ('all', 'Все время'),
    ]
    
    period = forms.ChoiceField(
        label='Период',
        choices=PERIOD_CHOICES,
        initial='month',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    group_by = forms.ChoiceField(
        label='Группировать по',
        choices=[
            ('day', 'Дням'),
            ('week', 'Неделям'),
            ('month', 'Месяцам'),
            ('year', 'Годам'),
        ],
        initial='month',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )


class SupportTicketForm(forms.Form):
    """
    Форма обращения в поддержку
    """
    TICKET_TYPES = [
        ('order', 'Заказ'),
        ('payment', 'Платеж'),
        ('delivery', 'Доставка'),
        ('return', 'Возврат'),
        ('technical', 'Техническая проблема'),
        ('other', 'Другое'),
    ]
    
    ticket_type = forms.ChoiceField(
        label='Тип обращения',
        choices=TICKET_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    subject = forms.CharField(
        label='Тема',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Кратко опишите проблему'
        })
    )
    
    message = forms.CharField(
        label='Сообщение',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Подробно опишите вашу проблему...'
        })
    )
    
    order_number = forms.CharField(
        label='Номер заказа',
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Если проблема связана с заказом'
        })
    )
    
    priority = forms.ChoiceField(
        label='Приоритет',
        choices=[
            ('low', 'Низкий'),
            ('medium', 'Средний'),
            ('high', 'Высокий'),
            ('urgent', 'Срочный'),
        ],
        initial='medium',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )


class LoyaltyProgramForm(forms.Form):
    """
    Форма программы лояльности
    """
    REWARD_CHOICES = [
        ('discount_5', 'Скидка 5% - 1000 баллов'),
        ('discount_10', 'Скидка 10% - 2000 баллов'),
        ('discount_15', 'Скидка 15% - 3000 баллов'),
        ('free_delivery', 'Бесплатная доставка - 500 баллов'),
        ('gift', 'Подарок - 1500 баллов'),
        ('vip_support', 'VIP поддержка - 2500 баллов'),
    ]
    
    reward = forms.ChoiceField(
        label='Выберите награду',
        choices=REWARD_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    confirm_spend = forms.BooleanField(
        label='Подтверждаю списание бонусных баллов',
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'required': True
        })
    )


class ExportUserDataForm(forms.Form):
    """
    Форма экспорта данных пользователя
    """
    EXPORT_TYPES = [
        ('profile', 'Профиль пользователя'),
        ('orders', 'История заказов'),
        ('addresses', 'Адреса доставки'),
        ('bonuses', 'Бонусная история'),
        ('wishlist', 'Список избранного'),
        ('reviews', 'Отзывы'),
        ('all', 'Все данные'),
    ]
    
    export_type = forms.ChoiceField(
        label='Тип данных для экспорта',
        choices=EXPORT_TYPES,
        initial='all',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    format = forms.ChoiceField(
        label='Формат файла',
        choices=[
            ('json', 'JSON'),
            ('csv', 'CSV'),
            ('xml', 'XML'),
        ],
        initial='json',
        widget=forms.Select(attrs={
            'class': 'form-select'
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
    
    password_confirm = forms.CharField(
        label='Подтвердите пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль для подтверждения'
        })
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.user = user
    
    def clean_password_confirm(self):
        password = self.cleaned_data['password_confirm']
        if not self.user.check_password(password):
            raise ValidationError('Неверный пароль')
        return password