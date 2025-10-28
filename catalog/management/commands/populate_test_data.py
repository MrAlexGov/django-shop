"""
Django management команда для заполнения сайта тестовыми данными
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from decimal import Decimal
from catalog.models import Category, Brand, ProductSpecification, Product, ProductImage, ProductSpecificationValue
from accounts.models import User


class Command(BaseCommand):
    help = 'Заполнить сайт тестовыми данными и товарами'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Начало заполнения тестовыми данными...'))
        
        # Создаем категории
        self.create_categories()
        
        # Создаем бренды
        self.create_brands()
        
        # Создаем характеристики
        self.create_specifications()
        
        # Создаем пользователей
        self.create_users()
        
        # Создаем товары
        self.create_products()
        
        self.stdout.write(self.style.SUCCESS('Тестовые данные успешно созданы!'))

    def create_categories(self):
        """Создание категорий товаров"""
        self.stdout.write('Создание категорий...')
        
        categories_data = [
            {
                'name': 'Смартфоны',
                'description': 'Мобильные телефоны и смартфоны различных брендов',
                'sort_order': 1,
                'is_active': True
            },
            {
                'name': 'Умные часы',
                'description': 'Умные часы и фитнес-трекеры',
                'sort_order': 2,
                'is_active': True
            },
            {
                'name': 'Наушники',
                'description': 'Беспроводные и проводные наушники',
                'sort_order': 3,
                'is_active': True
            },
            {
                'name': 'Аксессуары',
                'description': 'Чехлы, кабели, зарядные устройства и другие аксессуары',
                'sort_order': 4,
                'is_active': True
            },
            {
                'name': 'Планшеты',
                'description': 'Планшетные компьютеры',
                'sort_order': 5,
                'is_active': True
            }
        ]
        
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                slug=slugify(cat_data['name']),
                defaults=cat_data
            )
            if created:
                self.stdout.write(f'Создана категория: {category.name}')
            else:
                self.stdout.write(f'Категория уже существует: {category.name}')

    def create_brands(self):
        """Создание брендов товаров"""
        self.stdout.write('Создание брендов...')
        
        brands_data = [
            {
                'name': 'Apple',
                'description': 'Американская компания, производитель iPhone, iPad и других устройств',
                'website': 'https://www.apple.com',
                'sort_order': 1,
                'is_active': True
            },
            {
                'name': 'Samsung',
                'description': 'Южнокорейская компания, производитель смартфонов Galaxy',
                'website': 'https://www.samsung.com',
                'sort_order': 2,
                'is_active': True
            },
            {
                'name': 'Xiaomi',
                'description': 'Китайская компания, производитель смартфонов Redmi и Mi',
                'website': 'https://www.mi.com',
                'sort_order': 3,
                'is_active': True
            },
            {
                'name': 'Honor',
                'description': 'Китайская компания, производитель смартфонов Honor',
                'website': 'https://www.hihonor.com',
                'sort_order': 4,
                'is_active': True
            },
            {
                'name': 'Huawei',
                'description': 'Китайская компания, производитель смартфонов Huawei',
                'website': 'https://www.huawei.com',
                'sort_order': 5,
                'is_active': True
            },
            {
                'name': 'OnePlus',
                'description': 'Китайская компания, производитель смартфонов OnePlus',
                'website': 'https://www.oneplus.com',
                'sort_order': 6,
                'is_active': True
            },
            {
                'name': 'Realme',
                'description': 'Китайская компания, производитель смартфонов Realme',
                'website': 'https://www.realme.com',
                'sort_order': 7,
                'is_active': True
            },
            {
                'name': 'Sony',
                'description': 'Японская компания, производитель смартфонов Xperia',
                'website': 'https://www.sony.com',
                'sort_order': 8,
                'is_active': True
            }
        ]
        
        for brand_data in brands_data:
            brand, created = Brand.objects.get_or_create(
                slug=slugify(brand_data['name']),
                defaults=brand_data
            )
            if created:
                self.stdout.write(f'Создан бренд: {brand.name}')
            else:
                self.stdout.write(f'Бренд уже существует: {brand.name}')

    def create_specifications(self):
        """Создание характеристик товаров"""
        self.stdout.write('Создание характеристик...')
        
        # Характеристики для смартфонов
        smartphone_category = Category.objects.filter(name='Смартфоны').first()
        if not smartphone_category:
            self.stdout.write(self.style.ERROR('Категория "Смартфоны" не найдена!'))
            return
        
        specifications_data = [
            {'name': 'Экран', 'category': smartphone_category, 'value_type': 'text', 'sort_order': 1},
            {'name': 'Разрешение экрана', 'category': smartphone_category, 'value_type': 'text', 'sort_order': 2},
            {'name': 'Процессор', 'category': smartphone_category, 'value_type': 'text', 'sort_order': 3},
            {'name': 'Оперативная память', 'category': smartphone_category, 'value_type': 'number', 'unit': 'ГБ', 'sort_order': 4},
            {'name': 'Встроенная память', 'category': smartphone_category, 'value_type': 'number', 'unit': 'ГБ', 'sort_order': 5},
            {'name': 'Основная камера', 'category': smartphone_category, 'value_type': 'text', 'sort_order': 6},
            {'name': 'Фронтальная камера', 'category': smartphone_category, 'value_type': 'text', 'sort_order': 7},
            {'name': 'Аккумулятор', 'category': smartphone_category, 'value_type': 'number', 'unit': 'мА·ч', 'sort_order': 8},
            {'name': 'ОС', 'category': smartphone_category, 'value_type': 'text', 'sort_order': 9},
            {'name': 'Вес', 'category': smartphone_category, 'value_type': 'number', 'unit': 'г', 'sort_order': 10}
        ]
        
        for spec_data in specifications_data:
            spec, created = ProductSpecification.objects.get_or_create(
                name=spec_data['name'],
                category=spec_data['category'],
                defaults=spec_data
            )
            if created:
                self.stdout.write(f'Создана характеристика: {spec.name}')
            else:
                self.stdout.write(f'Характеристика уже существует: {spec.name}')

    def create_users(self):
        """Создание тестовых пользователей"""
        self.stdout.write('Создание тестовых пользователей...')
        
        users_data = [
            {
                'username': 'testuser1',
                'email': 'test1@example.com',
                'first_name': 'Иван',
                'last_name': 'Петров',
                'password': 'testpass123'
            },
            {
                'username': 'testuser2',
                'email': 'test2@example.com',
                'first_name': 'Мария',
                'last_name': 'Иванова',
                'password': 'testpass123'
            },
            {
                'username': 'testuser3',
                'email': 'test3@example.com',
                'first_name': 'Алексей',
                'last_name': 'Сидоров',
                'password': 'testpass123'
            }
        ]
        
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults=user_data
            )
            if created:
                user.set_password(user_data['password'])
                user.save()
                self.stdout.write(f'Создан пользователь: {user.username}')
            else:
                self.stdout.write(f'Пользователь уже существует: {user.username}')

    def create_products(self):
        """Создание товаров"""
        self.stdout.write('Создание товаров...')
        
        # Получаем категории и бренды
        smartphone_category = Category.objects.filter(name='Смартфоны').first()
        if not smartphone_category:
            self.stdout.write(self.style.ERROR('Категория "Смартфоны" не найдена!'))
            return
            
        apple_brand = Brand.objects.filter(name='Apple').first()
        samsung_brand = Brand.objects.filter(name='Samsung').first()
        xiaomi_brand = Brand.objects.filter(name='Xiaomi').first()
        honor_brand = Brand.objects.filter(name='Honor').first()
        
        if not all([smartphone_category, apple_brand, samsung_brand, xiaomi_brand, honor_brand]):
            self.stdout.write(self.style.ERROR('Не все необходимые категории и бренды найдены!'))
            return
        
        products_data = [
            # Apple товары
            {
                'name': 'iPhone 15 Pro',
                'sku': 'IPH15P-128-BLU',
                'category': smartphone_category,
                'brand': apple_brand,
                'price': Decimal('89990.00'),
                'old_price': Decimal('99990.00'),
                'stock_quantity': 15,
                'short_description': 'Флагманский iPhone с чипом A17 Pro',
                'description': 'iPhone 15 Pro - это новейший флагманский смартфон Apple с титановым корпусом, чипом A17 Pro и улучшенной камерой.',
                'is_featured': True,
                'is_bestseller': True,
                'is_new': True,
                'is_discount': False
            },
            {
                'name': 'iPhone 14',
                'sku': 'IPH14-128-BLK',
                'category': smartphone_category,
                'brand': apple_brand,
                'price': Decimal('69990.00'),
                'old_price': Decimal('79990.00'),
                'stock_quantity': 25,
                'short_description': 'Надежный iPhone с отличной камерой',
                'description': 'iPhone 14 предлагает отличную производительность и качественную камеру по доступной цене.',
                'is_featured': True,
                'is_bestseller': True,
                'is_new': False,
                'is_discount': False
            },
            {
                'name': 'iPhone SE',
                'sku': 'IPHSE-64-RED',
                'category': smartphone_category,
                'brand': apple_brand,
                'price': Decimal('44990.00'),
                'old_price': None,
                'stock_quantity': 10,
                'short_description': 'Доступный iPhone с мощным процессором',
                'description': 'iPhone SE - это самый доступный способ войти в экосистему Apple.',
                'is_featured': False,
                'is_bestseller': False,
                'is_new': True,
                'is_discount': False
            },
            
            # Samsung товары
            {
                'name': 'Galaxy S24 Ultra',
                'sku': 'SGS24U-256-BLK',
                'category': smartphone_category,
                'brand': samsung_brand,
                'price': Decimal('99990.00'),
                'old_price': Decimal('119990.00'),
                'stock_quantity': 12,
                'short_description': 'Премиальный Samsung с S Pen',
                'description': 'Galaxy S24 Ultra - это флагманский смартфон Samsung с встроенным стилусом S Pen и мощной камерой.',
                'is_featured': True,
                'is_bestseller': True,
                'is_new': True,
                'is_discount': False
            },
            {
                'name': 'Galaxy A54',
                'sku': 'SGA54-128-WHT',
                'category': smartphone_category,
                'brand': samsung_brand,
                'price': Decimal('34990.00'),
                'old_price': Decimal('39990.00'),
                'stock_quantity': 30,
                'short_description': 'Стильный смартфон среднего класса',
                'description': 'Galaxy A54 - это смартфон среднего класса с отличным экраном и хорошей камерой.',
                'is_featured': True,
                'is_bestseller': False,
                'is_new': False,
                'is_discount': False
            },
            
            # Xiaomi товары
            {
                'name': 'Xiaomi 14',
                'sku': 'XM14-256-BLU',
                'category': smartphone_category,
                'brand': xiaomi_brand,
                'price': Decimal('59990.00'),
                'old_price': Decimal('69990.00'),
                'stock_quantity': 20,
                'short_description': 'Производительный смартфон с быстрой зарядкой',
                'description': 'Xiaomi 14 предлагает высокую производительность и поддержку быстрой зарядки 90 Вт.',
                'is_featured': True,
                'is_bestseller': True,
                'is_new': True,
                'is_discount': False
            },
            {
                'name': 'Redmi Note 13',
                'sku': 'RDN13-128-GRN',
                'category': smartphone_category,
                'brand': xiaomi_brand,
                'price': Decimal('24990.00'),
                'old_price': None,
                'stock_quantity': 40,
                'short_description': 'Доступный смартфон с большой батареей',
                'description': 'Redmi Note 13 - это доступный смартфон с большой батареей 5000 мА·ч.',
                'is_featured': False,
                'is_bestseller': True,
                'is_new': False,
                'is_discount': False
            },
            
            # Honor товары
            {
                'name': 'Honor 90',
                'sku': 'HON90-256-PNK',
                'category': smartphone_category,
                'brand': honor_brand,
                'price': Decimal('39990.00'),
                'old_price': Decimal('44990.00'),
                'stock_quantity': 18,
                'short_description': 'Смартфон с элегантным дизайном',
                'description': 'Honor 90 выделяется своим элегантным дизайном и качественными материалами.',
                'is_featured': True,
                'is_bestseller': False,
                'is_new': True,
                'is_discount': False
            }
        ]
        
        # Создаем товары
        created_products = []
        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                sku=product_data['sku'],
                defaults=product_data
            )
            if created:
                created_products.append(product)
                self.stdout.write(f'Создан товар: {product.name}')
            else:
                self.stdout.write(f'Товар уже существует: {product.name}')
        
        # Создаем изображения для товаров
        self.create_product_images(created_products)
        
        # Создаем характеристики для товаров
        self.create_product_specifications(created_products)

    def create_product_images(self, products):
        """Создание изображений товаров"""
        self.stdout.write('Создание изображений товаров...')
        
        for product in products:
            # Создаем основное изображение
            image, created = ProductImage.objects.get_or_create(
                product=product,
                is_main=True,
                defaults={
                    'alt_text': f'{product.name} - основное изображение',
                    'sort_order': 0
                }
            )
            if created:
                self.stdout.write(f'Создано основное изображение для {product.name}')
            else:
                self.stdout.write(f'Изображение для {product.name} уже существует')

    def create_product_specifications(self, products):
        """Создание характеристик товаров"""
        self.stdout.write('Создание характеристик товаров...')
        
        # Получаем характеристики
        specs = ProductSpecification.objects.all()
        
        for product in products:
            # Заполняем характеристики в зависимости от бренда и модели
            if 'iPhone 15 Pro' in product.name:
                spec_values = {
                    'Экран': '6.1" OLED',
                    'Разрешение экрана': '2556×1179 пикселей',
                    'Процессор': 'A17 Pro',
                    'Оперативная память': 8,
                    'Встроенная память': 128,
                    'Основная камера': '48 МП + 12 МП + 12 МП',
                    'Фронтальная камера': '12 МП',
                    'Аккумулятор': 3274,
                    'ОС': 'iOS 17',
                    'Вес': 187
                }
            elif 'iPhone 14' in product.name:
                spec_values = {
                    'Экран': '6.1" OLED',
                    'Разрешение экрана': '2532×1170 пикселей',
                    'Процессор': 'A15 Bionic',
                    'Оперативная память': 6,
                    'Встроенная память': 128,
                    'Основная камера': '12 МП + 12 МП',
                    'Фронтальная камера': '12 МП',
                    'Аккумулятор': 3279,
                    'ОС': 'iOS 16',
                    'Вес': 172
                }
            elif 'Galaxy S24 Ultra' in product.name:
                spec_values = {
                    'Экран': '6.8" Dynamic AMOLED 2X',
                    'Разрешение экрана': '3120×1440 пикселей',
                    'Процессор': 'Snapdragon 8 Gen 3',
                    'Оперативная память': 12,
                    'Встроенная память': 256,
                    'Основная камера': '200 МП + 50 МП + 12 МП + 10 МП',
                    'Фронтальная камера': '12 МП',
                    'Аккумулятор': 5000,
                    'ОС': 'Android 14',
                    'Вес': 232
                }
            elif 'Xiaomi 14' in product.name:
                spec_values = {
                    'Экран': '6.36" AMOLED',
                    'Разрешение экрана': '2670×1200 пикселей',
                    'Процессор': 'Snapdragon 8 Gen 3',
                    'Оперативная память': 12,
                    'Встроенная память': 256,
                    'Основная камера': '50 МП + 50 МП + 50 МП',
                    'Фронтальная камера': '32 МП',
                    'Аккумулятор': 4610,
                    'ОС': 'Android 14 (HyperOS)',
                    'Вес': 193
                }
            else:
                # Общие характеристики для остальных товаров
                spec_values = {
                    'Экран': '6.5" Full HD+',
                    'Разрешение экрана': '2400×1080 пикселей',
                    'Процессор': '8-ядерный',
                    'Оперативная память': 8,
                    'Встроенная память': 128,
                    'Основная камера': '64 МП',
                    'Фронтальная камера': '16 МП',
                    'Аккумулятор': 4000,
                    'ОС': 'Android 13',
                    'Вес': 180
                }
            
            # Создаем значения характеристик
            for spec_name, value in spec_values.items():
                try:
                    spec = specs.get(name=spec_name)
                    spec_value, created = ProductSpecificationValue.objects.get_or_create(
                        product=product,
                        specification=spec,
                        defaults=self.get_spec_value(spec, value)
                    )
                    if created:
                        self.stdout.write(f'Создана характеристика {spec_name} для {product.name}')
                    else:
                        self.stdout.write(f'Характеристика {spec_name} для {product.name} уже существует')
                except ProductSpecification.DoesNotExist:
                    continue

    def get_spec_value(self, specification, value):
        """Получить значение характеристики в зависимости от типа"""
        if specification.value_type == 'text':
            return {'value_text': str(value)}
        elif specification.value_type == 'number':
            return {'value_number': value}
        elif specification.value_type == 'boolean':
            return {'value_boolean': bool(value)}
        elif specification.value_type == 'list':
            return {'value_list': str(value)}
        return {'value_text': str(value)}