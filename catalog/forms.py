"""
Формы для приложения catalog (каталог товаров)
"""

from django import forms
from django.db.models import Q
from .models import Category, Brand, Product, ProductSpecification, Review
from accounts.models import User


class ProductFilterForm(forms.Form):
    """
    Форма фильтрации товаров
    """
    # Основные фильтры
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True),
        required=False,
        empty_label='Все категории',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'category-filter'
        })
    )
    
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.filter(is_active=True),
        required=False,
        empty_label='Все бренды',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'brand-filter'
        })
    )
    
    # Фильтр по цене
    min_price = forms.DecimalField(
        label='Цена от',
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0',
            'id': 'min-price'
        })
    )
    
    max_price = forms.DecimalField(
        label='Цена до',
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '100000',
            'id': 'max-price'
        })
    )
    
    # Фильтр по наличию
    in_stock = forms.BooleanField(
        label='Только в наличии',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'in-stock-filter'
        })
    )
    
    # Характеристики согласно ТЗ
    
    # Оперативная память
    ram = forms.ChoiceField(
        label='Оперативная память',
        required=False,
        choices=[
            ('', 'Любая'),
            (4, '4 ГБ'),
            (6, '6 ГБ'),
            (8, '8 ГБ'),
            (12, '12 ГБ'),
            (16, '16 ГБ'),
            (32, '32 ГБ'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'ram-filter'
        })
    )
    
    # Объем встроенной памяти
    storage = forms.ChoiceField(
        label='Встроенная память',
        required=False,
        choices=[
            ('', 'Любая'),
            (32, '32 ГБ'),
            (64, '64 ГБ'),
            (128, '128 ГБ'),
            (256, '256 ГБ'),
            (512, '512 ГБ'),
            (1024, '1 ТБ'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'storage-filter'
        })
    )
    
    # Диагональ экрана
    screen_size = forms.ChoiceField(
        label='Диагональ экрана',
        required=False,
        choices=[
            ('', 'Любая'),
            (5.0, '5.0"'),
            (5.5, '5.5"'),
            (6.0, '6.0"'),
            (6.1, '6.1"'),
            (6.2, '6.2"'),
            (6.3, '6.3"'),
            (6.4, '6.4"'),
            (6.5, '6.5"'),
            (6.6, '6.6"'),
            (6.7, '6.7"'),
            (6.8, '6.8"'),
            (6.9, '6.9"'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'screen-size-filter'
        })
    )
    
    # Процессор (текстовый фильтр)
    processor = forms.CharField(
        label='Процессор',
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например: Snapdragon, Apple A17, Exynos',
            'id': 'processor-filter'
        })
    )
    
    # Операционная система
    os = forms.ChoiceField(
        label='Операционная система',
        required=False,
        choices=[
            ('', 'Любая'),
            ('Android', 'Android'),
            ('iOS', 'iOS'),
            ('HarmonyOS', 'HarmonyOS'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'os-filter'
        })
    )
    
    # Количество SIM-карт
    sim_slots = forms.ChoiceField(
        label='Количество SIM-карт',
        required=False,
        choices=[
            ('', 'Любое'),
            (1, '1 SIM'),
            (2, '2 SIM'),
            (3, '3 SIM'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'sim-slots-filter'
        })
    )
    
    # Поддержка 5G
    support_5g = forms.BooleanField(
        label='Поддержка 5G',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'support-5g-filter'
        })
    )
    
    # Беспроводная зарядка
    wireless_charging = forms.BooleanField(
        label='Беспроводная зарядка',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'wireless-charging-filter'
        })
    )
    
    # Водозащита
    water_resistance = forms.BooleanField(
        label='Водозащита',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'water-resistance-filter'
        })
    )
    
    # Сканер отпечатков
    fingerprint_scanner = forms.ChoiceField(
        label='Сканер отпечатков',
        required=False,
        choices=[
            ('', 'Любой'),
            ('none', 'Нет'),
            ('rear', 'Сзади'),
            ('side', 'Сбоку'),
            ('under_display', 'Под экраном'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'fingerprint-scanner-filter'
        })
    )
    
    # Цвет
    color = forms.CharField(
        label='Цвет',
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например: черный, белый, золотой',
            'id': 'color-filter'
        })
    )
    
    # Сортировка
    sort_by = forms.ChoiceField(
        label='Сортировать по',
        required=False,
        choices=[
            ('', 'По популярности'),
            ('name', 'По названию'),
            ('price', 'По цене'),
            ('price_desc', 'По цене (убыв.)'),
            ('rating', 'По рейтингу'),
            ('newest', 'Сначала новинки'),
            ('sales_count', 'По популярности'),
            ('views_count', 'По просмотрам'),
            ('created_at', 'Дате добавления'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'sort-by-filter'
        })
    )
    
    # Отображать только товары со скидкой
    on_sale = forms.BooleanField(
        label='Только со скидкой',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'on-sale-filter'
        })
    )
    
    # Отображать только рекомендуемые товары
    featured = forms.BooleanField(
        label='Только рекомендуемые',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'featured-filter'
        })
    )
    
    # Отображать только хиты продаж
    bestseller = forms.BooleanField(
        label='Только хиты продаж',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'bestseller-filter'
        })
    )


class ProductSearchForm(forms.Form):
    """
    Форма поиска товаров с автодополнением
    """
    q = forms.CharField(
        label='Поиск',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Поиск товаров, брендов, характеристик...',
            'id': 'search-input',
            'autocomplete': 'off'
        })
    )
    
    search_type = forms.ChoiceField(
        label='Тип поиска',
        required=False,
        choices=[
            ('all', 'Все'),
            ('products', 'Товары'),
            ('brands', 'Бренды'),
            ('categories', 'Категории'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'search-type'
        })
    )
    
    def clean_q(self):
        query = self.cleaned_data.get('q', '').strip()
        if query and len(query) < 2:
            raise forms.ValidationError('Поисковый запрос должен содержать минимум 2 символа')
        return query


class ReviewForm(forms.ModelForm):
    """
    Форма для добавления и редактирования отзывов
    """
    RATING_CHOICES = [
        (5, '5 - Отлично'),
        (4, '4 - Хорошо'),
        (3, '3 - Удовлетворительно'),
        (2, '2 - Плохо'),
        (1, '1 - Очень плохо'),
    ]
    
    rating = forms.ChoiceField(
        label='Рейтинг',
        choices=RATING_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    title = forms.CharField(
        label='Заголовок отзыва',
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Краткое описание вашего мнения'
        })
    )
    
    text = forms.CharField(
        label='Текст отзыва',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Поделитесь подробным мнением о товаре...'
        })
    )
    
    pros = forms.CharField(
        label='Достоинства',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Что вам понравилось в товаре?'
        })
    )
    
    cons = forms.CharField(
        label='Недостатки',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Что вам не понравилось?'
        })
    )
    
    is_recommended = forms.BooleanField(
        label='Рекомендую этот товар',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    class Meta:
        model = Review
        fields = ('rating', 'title', 'text', 'pros', 'cons', 'is_recommended')
    
    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if not rating or not rating.isdigit() or int(rating) < 1 or int(rating) > 5:
            raise forms.ValidationError('Рейтинг должен быть от 1 до 5')
        return int(rating)
    
    def clean_text(self):
        text = self.cleaned_data.get('text')
        if text and len(text) < 20:
            raise forms.ValidationError('Отзыв должен содержать минимум 20 символов')
        return text


class AdvancedSearchForm(forms.Form):
    """
    Форма расширенного поиска
    """
    # Базовые поля
    q = forms.CharField(
        label='Поисковая фраза',
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ключевые слова'
        })
    )
    
    # Фильтры
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True),
        required=False,
        empty_label='Все категории',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.filter(is_active=True),
        required=False,
        empty_label='Все бренды',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    # Диапазон цен
    min_price = forms.DecimalField(
        label='Цена от',
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control'
        })
    )
    
    max_price = forms.DecimalField(
        label='Цена до',
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control'
        })
    )
    
    # Рейтинг
    min_rating = forms.ChoiceField(
        label='Минимальный рейтинг',
        required=False,
        choices=[
            ('', 'Любой'),
            (5, '5 звезд'),
            (4, '4 звезды и выше'),
            (3, '3 звезды и выше'),
            (2, '2 звезды и выше'),
            (1, '1 звезда и выше'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    # Наличие
    in_stock = forms.BooleanField(
        label='Только в наличии',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    # Специальные фильтры
    only_reviews = forms.BooleanField(
        label='Только с отзывами',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    new_products = forms.BooleanField(
        label='Только новинки',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    sale_products = forms.BooleanField(
        label='Только со скидкой',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    # Настройки поиска
    search_fields = forms.MultipleChoiceField(
        label='Где искать',
        required=False,
        choices=[
            ('name', 'Название товара'),
            ('description', 'Описание'),
            ('brand', 'Бренд'),
            ('category', 'Категория'),
            ('specifications', 'Характеристики'),
            ('tags', 'Теги'),
        ],
        initial=['name', 'description', 'brand', 'category'],
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        })
    )
    
    match_type = forms.ChoiceField(
        label='Тип совпадения',
        choices=[
            ('all', 'Все слова'),
            ('any', 'Любое слово'),
            ('exact', 'Точная фраза'),
        ],
        initial='all',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )


class CompareProductsForm(forms.Form):
    """
    Форма для сравнения товаров
    """
    products = forms.ModelMultipleChoiceField(
        queryset=Product.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=False
    )
    
    comparison_fields = forms.MultipleChoiceField(
        label='Поля для сравнения',
        choices=[
            ('price', 'Цена'),
            ('brand', 'Бренд'),
            ('category', 'Категория'),
            ('ram', 'Оперативная память'),
            ('storage', 'Встроенная память'),
            ('screen_size', 'Размер экрана'),
            ('battery_capacity', 'Емкость аккумулятора'),
            ('camera', 'Камера'),
            ('os', 'Операционная система'),
            ('processor', 'Процессор'),
            ('warranty', 'Гарантия'),
        ],
        initial=['price', 'brand', 'ram', 'storage', 'screen_size'],
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        })
    )


class ProductSuggestionForm(forms.Form):
    """
    Форма для получения предложений товаров
    """
    product_id = forms.IntegerField(widget=forms.HiddenInput())
    suggestion_type = forms.ChoiceField(
        label='Тип предложения',
        choices=[
            ('similar', 'Похожие товары'),
            ('related', 'Связанные товары'),
            ('alternatives', 'Альтернативы'),
            ('upgrades', 'Улучшения'),
            ('bundles', 'Комплекты'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )


class WishlistForm(forms.Form):
    """
    Форма для работы с избранным
    """
    product_id = forms.IntegerField(widget=forms.HiddenInput())
    action = forms.ChoiceField(
        label='Действие',
        choices=[
            ('add', 'Добавить'),
            ('remove', 'Удалить'),
        ],
        widget=forms.HiddenInput()
    )


class QuickSearchForm(forms.Form):
    """
    Форма быстрого поиска
    """
    q = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Быстрый поиск...',
            'id': 'quick-search'
        })
    )


class ProductSortForm(forms.Form):
    """
    Форма сортировки товаров
    """
    sort_by = forms.ChoiceField(
        choices=[
            ('name', 'По названию'),
            ('price', 'По цене'),
            ('price_desc', 'По цене (убыв.)'),
            ('rating', 'По рейтингу'),
            ('newest', 'Новинки'),
            ('popularity', 'Популярность'),
            ('sales_count', 'Продажи'),
            ('created_at', 'Дате добавления'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'onchange': 'this.form.submit()'
        })
    )


class ProductListForm(forms.Form):
    """
    Форма настройки отображения списка товаров
    """
    view_type = forms.ChoiceField(
        label='Вид отображения',
        choices=[
            ('grid', 'Сетка'),
            ('list', 'Список'),
            ('table', 'Таблица'),
        ],
        initial='grid',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    items_per_page = forms.ChoiceField(
        label='Товаров на странице',
        choices=[
            (12, '12'),
            (24, '24'),
            (48, '48'),
            (96, '96'),
        ],
        initial=24,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    show_filters = forms.BooleanField(
        label='Показывать фильтры',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    compact_view = forms.BooleanField(
        label='Компактный вид',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )