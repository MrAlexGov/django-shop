"""
Django management команда для полного сброса и заполнения данными
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from catalog.models import Category, Brand, ProductSpecification, Product, ProductImage, ProductSpecificationValue, Review
from accounts.models import User
from django.db import transaction


class Command(BaseCommand):
    help = 'Полный сброс и заполнение сайта тестовыми данными'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Подтвердить выполнение команды (требуется для автоматизации)',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.ERROR(
                    'ВНИМАНИЕ: Эта команда удалит все существующие данные в каталоге!\n'
                    'Для подтверждения выполните команду с параметром --confirm'
                )
            )
            return
        
        self.stdout.write(self.style.SUCCESS('Начало полного сброса и заполнения данными...'))
        
        try:
            with transaction.atomic():
                # 1. Сброс данных
                self.reset_data()
                
                # 2. Заполнение данными
                call_command('populate_test_data')
                call_command('create_reviews')
                
            self.stdout.write(self.style.SUCCESS('Все данные успешно сброшены и заполнены!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка: {str(e)}'))
            raise

    def reset_data(self):
        """Сброс всех данных каталога"""
        self.stdout.write('Сброс существующих данных...')
        
        # Удаляем в правильном порядке (из-за связей foreign key)
        Review.objects.all().delete()
        ProductSpecificationValue.objects.all().delete()
        ProductImage.objects.all().delete()
        Product.objects.all().delete()
        ProductSpecification.objects.all().delete()
        Brand.objects.all().delete()
        Category.objects.all().delete()
        
        self.stdout.write('Все данные каталога удалены')

    def reset_all(self):
        """Сброс всех данных включая пользователей"""
        self.stdout.write('Сброс всех данных включая пользователей...')
        
        # Удаляем в правильном порядке
        Review.objects.all().delete()
        ProductSpecificationValue.objects.all().delete()
        ProductImage.objects.all().delete()
        Product.objects.all().delete()
        ProductSpecification.objects.all().delete()
        Brand.objects.all().delete()
        Category.objects.all().delete()
        User.objects.all().delete()
        
        self.stdout.write('Все данные удалены')