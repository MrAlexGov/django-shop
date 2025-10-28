"""
Django management команда для создания отзывов пользователей о товарах
"""

from django.core.management.base import BaseCommand
from catalog.models import Product, Review
from accounts.models import User


class Command(BaseCommand):
    help = 'Создать отзывы пользователей о товарах'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Начало создания отзывов...'))
        
        # Создаем отзывы для товаров
        self.create_reviews()
        
        self.stdout.write(self.style.SUCCESS('Отзывы успешно созданы!'))

    def create_reviews(self):
        """Создание отзывов пользователей"""
        self.stdout.write('Создание отзывов пользователей...')
        
        # Получаем все товары и пользователей
        products = Product.objects.all()
        users = User.objects.all()
        
        # Если нет пользователей, создаем тестового пользователя
        if not users.exists():
            user = User.objects.create_user(
                username='testuser',
                email='test@example.com',
                password='testpass123',
                first_name='Тест',
                last_name='Пользователь'
            )
            self.stdout.write('Создан тестовый пользователь')
        else:
            user = users.first()
        
        reviews_data = [
            {
                'product_name_contains': 'iPhone 15 Pro',
                'rating': 5,
                'title': 'Отличный флагман!',
                'text': 'Потрясающий смартфон с отличной камерой и производительностью. Титановый корпус выглядит премиально.',
                'pros': 'Отличная камера, высокая производительность, премиальные материалы',
                'cons': 'Высокая цена',
                'is_approved': True,
                'is_verified_purchase': True
            },
            {
                'product_name_contains': 'iPhone 15 Pro',
                'rating': 4,
                'title': 'Хороший, но дорогой',
                'text': 'В целом хороший смартфон, но цена завышена. Камера действительно впечатляет.',
                'pros': 'Отличная камера, быстрый процессор',
                'cons': 'Высокая цена, небольшая емкость батареи',
                'is_approved': True,
                'is_verified_purchase': True
            },
            {
                'product_name_contains': 'iPhone 14',
                'rating': 4,
                'title': 'Надежный смартфон',
                'text': 'Пользуюсь уже полгода, никаких нареканий. Все работает стабильно.',
                'pros': 'Стабильная работа, хорошая камера',
                'cons': 'Нет USB-C, типичный дизайн',
                'is_approved': True,
                'is_verified_purchase': True
            },
            {
                'product_name_contains': 'Galaxy S24 Ultra',
                'rating': 5,
                'title': 'Лучший Android смартфон',
                'text': 'S Pen незаменим для работы, камера просто фантастическая. Лучший выбор для Android.',
                'pros': 'S Pen, отличная камера, большой экран',
                'cons': 'Большие размеры, высокая цена',
                'is_approved': True,
                'is_verified_purchase': True
            },
            {
                'product_name_contains': 'Galaxy S24 Ultra',
                'rating': 4,
                'title': 'Отличный флагман',
                'text': 'За свои деньги получаете отличный смартфон. Камера действительно впечатляет.',
                'pros': 'Мощный процессор, отличная камера, S Pen',
                'cons': 'Тяжелый, скользкий без чехла',
                'is_approved': True,
                'is_verified_purchase': True
            },
            {
                'product_name_contains': 'Xiaomi 14',
                'rating': 4,
                'title': 'Отличное соотношение цены и качества',
                'text': 'За такие деньги получаете отличные характеристики. Быстрая зарядка очень впечатляет.',
                'pros': 'Высокая производительность, быстрая зарядка, хорошая цена',
                'cons': 'MIUI не для всех, реклама в интерфейсе',
                'is_approved': True,
                'is_verified_purchase': True
            },
            {
                'product_name_contains': 'Xiaomi 14',
                'rating': 5,
                'title': 'Превосходно!',
                'text': 'Потрясающий смартфон за свою цену. Качество сборки на высшем уровне.',
                'pros': 'Отличное качество сборки, быстрая зарядка, яркий экран',
                'cons': 'Некоторые приложения не оптимизированы',
                'is_approved': True,
                'is_verified_purchase': True
            },
            {
                'product_name_contains': 'Redmi Note 13',
                'rating': 4,
                'title': 'Хороший бюджетник',
                'text': 'Для своей цены очень достойный смартфон. Батареи хватает на весь день.',
                'pros': 'Доступная цена, большая батарея, хороший экран',
                'cons': 'Камера среднего качества, пластиковый корпус',
                'is_approved': True,
                'is_verified_purchase': True
            },
            {
                'product_name_contains': 'Honor 90',
                'rating': 3,
                'title': 'Симпатичный дизайн',
                'text': 'Смартфон выглядит красиво, но производительность оставляет желать лучшего.',
                'pros': 'Красивый дизайн, хороший экран',
                'cons': 'Слабая производительность, камера не впечатляет',
                'is_approved': True,
                'is_verified_purchase': True
            },
            {
                'product_name_contains': 'Galaxy A54',
                'rating': 4,
                'title': 'Хороший средний сегмент',
                'text': 'Для повседневных задач подходит отлично. Камера делает неплохие снимки.',
                'pros': 'Хороший экран, стабильная работа, приятная цена',
                'cons': 'Камера среднего уровня, нет беспроводной зарядки',
                'is_approved': True,
                'is_verified_purchase': True
            },
            {
                'product_name_contains': 'iPhone SE',
                'rating': 4,
                'title': 'Лучший доступный iPhone',
                'text': 'Если нужен iOS по доступной цене - отличный выбор. Производительность на высоте.',
                'pros': 'Доступная цена для iPhone, высокая производительность',
                'cons': 'Устаревший дизайн, маленький экран, одна камера',
                'is_approved': True,
                'is_verified_purchase': True
            }
        ]
        
        created_reviews = 0
        for review_data in reviews_data:
            # Находим соответствующий товар
            product = products.filter(name__icontains=review_data['product_name_contains']).first()
            if not product:
                self.stdout.write(self.style.WARNING(f'Товар не найден: {review_data["product_name_contains"]}'))
                continue
            
            # Проверяем, есть ли уже отзыв от этого пользователя
            existing_review = Review.objects.filter(product=product, user=user).first()
            if existing_review:
                self.stdout.write(f'Отзыв для {product.name} от {user.username} уже существует')
                continue
            
            # Создаем отзыв
            review = Review.objects.create(
                product=product,
                user=user,
                rating=review_data['rating'],
                title=review_data['title'],
                text=review_data['text'],
                pros=review_data['pros'],
                cons=review_data['cons'],
                is_approved=review_data['is_approved'],
                is_verified_purchase=review_data['is_verified_purchase']
            )
            created_reviews += 1
            
            # Обновляем рейтинг товара
            self.update_product_rating(product)
            
            self.stdout.write(f'Создан отзыв для {product.name} от {user.username}')
        
        self.stdout.write(f'Создано {created_reviews} новых отзывов')

    def update_product_rating(self, product):
        """Обновить рейтинг товара на основе отзывов"""
        reviews = product.reviews.filter(is_approved=True)
        if reviews.exists():
            avg_rating = sum(review.rating for review in reviews) / reviews.count()
            product.rating = round(avg_rating, 2)
            product.reviews_count = reviews.count()
            product.save()
        else:
            product.rating = 0
            product.reviews_count = 0
            product.save()