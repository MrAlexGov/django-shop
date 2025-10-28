"""
Представления для приложения catalog (каталог товаров)
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Min, Max
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.conf import settings
import json
import csv
# import xlsxwriter  # Убрано для совместимости
from io import BytesIO
from datetime import datetime, timedelta

from .models import Category, Brand, Product, ProductImage, ProductSpecification, ProductSpecificationValue, Review
from accounts.models import Wishlist, CompareList
from cart.models import Cart, RecentlyViewed
from .forms import ProductFilterForm, ProductSearchForm, ReviewForm


def product_list(request):
    """
    Список всех товаров с фильтрацией и сортировкой
    """
    # Получаем параметры поиска
    search_query = request.GET.get('q', '').strip()

    # Получаем параметры фильтрации
    form = ProductFilterForm(request.GET)
    query = Product.objects.filter(is_active=True)

    # Применяем поиск
    if search_query:
        query = query.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(brand__name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    # Применяем фильтры
    if form.is_valid():
        # Фильтр по категории
        category = form.cleaned_data.get('category')
        if category:
            query = query.filter(category=category)

        # Фильтр по бренду
        brand = form.cleaned_data.get('brand')
        if brand:
            query = query.filter(brand=brand)

        # Фильтр по цене
        min_price = form.cleaned_data.get('min_price')
        max_price = form.cleaned_data.get('max_price')
        if min_price:
            query = query.filter(price__gte=min_price)
        if max_price:
            query = query.filter(price__lte=max_price)

        # Фильтр по наличию
        in_stock = form.cleaned_data.get('in_stock')
        if in_stock:
            query = query.filter(in_stock=True)

        # Фильтр по характеристикам
        ram = form.cleaned_data.get('ram')
        storage = form.cleaned_data.get('storage')
        screen_size = form.cleaned_data.get('screen_size')
        processor = form.cleaned_data.get('processor')

        if ram:
            query = query.filter(specifications__specification__name='Оперативная память',
                                specifications__value_number__gte=ram)
        if storage:
            query = query.filter(specifications__specification__name='Встроенная память',
                                specifications__value_number__gte=storage)
        if screen_size:
            query = query.filter(specifications__specification__name='Диагональ экрана',
                                specifications__value_number=screen_size)
        if processor:
            query = query.filter(specifications__specification__name='Процессор',
                                specifications__value_text__icontains=processor)

    # Сортировка
    sort_by = request.GET.get('sort', 'name')
    sort_order = request.GET.get('order', 'asc')

    sort_options = {
        'name': 'name',
        'price': 'price',
        'rating': 'rating',
        'newest': '-created_at',
        'popularity': '-sales_count',
        'views': '-views_count',
    }

    sort_field = sort_options.get(sort_by, 'name')
    if sort_order == 'desc':
        if sort_field.startswith('-'):
            sort_field = sort_field[1:]
        else:
            sort_field = f'-{sort_field}'

    query = query.select_related('category', 'brand').prefetch_related('images').order_by(sort_field)

    # Пагинация
    paginator = Paginator(query, 20)  # 20 товаров на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Получаем статистику для фильтров
    categories = Category.objects.filter(is_active=True).annotate(product_count=Count('products'))
    brands = Brand.objects.filter(is_active=True).annotate(products_count=Count('products'))
    price_range = query.aggregate(min_price=Min('price'), max_price=Max('price'))

    context = {
        'page_obj': page_obj,
        'form': form,
        'categories': categories,
        'brands': brands,
        'price_range': price_range,
        'total_products': query.count(),
        'current_sort': sort_by,
        'current_order': sort_order,
        'search_query': search_query,
    }

    return render(request, 'catalog/product_list.html', context)


def category_detail(request, slug):
    """
    Страница категории товаров
    """
    category = get_object_or_404(Category, slug=slug, is_active=True)
    
    # Получаем товары категории
    products = Product.objects.filter(category=category, is_active=True)
    
    # Применяем фильтры
    form = ProductFilterForm(request.GET)
    if form.is_valid():
        # Фильтрация по аналогии с product_list
        min_price = form.cleaned_data.get('min_price')
        max_price = form.cleaned_data.get('max_price')
        in_stock = form.cleaned_data.get('in_stock')
        
        if min_price:
            products = products.filter(price__gte=min_price)
        if max_price:
            products = products.filter(price__lte=max_price)
        if in_stock:
            products = products.filter(in_stock=True)
    
    # Сортировка
    sort_by = request.GET.get('sort', 'name')
    sort_options = {
        'name': 'name',
        'price': 'price',
        'rating': 'rating',
        'newest': '-created_at',
        'popularity': '-sales_count',
    }
    
    sort_field = sort_options.get(sort_by, 'name')
    products = products.select_related('category', 'brand').prefetch_related('images').order_by(sort_field)
    
    # Пагинация
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Подкатегории
    subcategories = category.children_categories
    
    context = {
        'category': category,
        'subcategories': subcategories,
        'page_obj': page_obj,
        'form': form,
        'total_products': products.count(),
    }
    
    return render(request, 'catalog/category_detail.html', context)


def brand_detail(request, slug):
    """
    Страница бренда
    """
    brand = get_object_or_404(Brand, slug=slug, is_active=True)
    
    # Получаем товары бренда
    products = Product.objects.filter(brand=brand, is_active=True)
    
    # Применяем фильтры
    form = ProductFilterForm(request.GET)
    if form.is_valid():
        min_price = form.cleaned_data.get('min_price')
        max_price = form.cleaned_data.get('max_price')
        in_stock = form.cleaned_data.get('in_stock')
        
        if min_price:
            products = products.filter(price__gte=min_price)
        if max_price:
            products = products.filter(price__lte=max_price)
        if in_stock:
            products = products.filter(in_stock=True)
    
    # Сортировка
    sort_by = request.GET.get('sort', 'name')
    sort_options = {
        'name': 'name',
        'price': 'price',
        'rating': 'rating',
        'newest': '-created_at',
        'popularity': '-sales_count',
    }
    
    sort_field = sort_options.get(sort_by, 'name')
    products = products.select_related('category', 'brand').prefetch_related('images').order_by(sort_field)
    
    # Пагинация
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'brand': brand,
        'page_obj': page_obj,
        'form': form,
        'total_products': products.count(),
    }
    
    return render(request, 'catalog/brand_detail.html', context)


def product_detail(request, slug):
    """
    Детальная страница товара
    """
    product = get_object_or_404(Product, slug=slug, is_active=True)
    
    # Увеличиваем счетчик просмотров
    product.views_count += 1
    product.save(update_fields=['views_count'])
    
    # Добавляем в недавно просмотренные
    if request.user.is_authenticated:
        RecentlyViewed.objects.update_or_create(
            user=request.user,
            product=product,
            defaults={'viewed_at': datetime.now()}
        )
    
    # Получаем изображения товара
    images = product.get_all_images()
    
    # Получаем характеристики
    specifications = product.get_specifications()
    
    # Получаем отзывы
    reviews = product.reviews.filter(is_approved=True).select_related('user')
    
    # Похожие товары
    related_products = product.get_related_products()[:4]
    
    # Проверяем, в избранном ли товар
    in_wishlist = False
    in_compare = False
    
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()
        in_compare = CompareList.objects.filter(user=request.user, product=product).exists()
    
    # Средний рейтинг
    rating_stats = reviews.aggregate(
        avg_rating=Avg('rating'),
        total_reviews=Count('id')
    )
    
    # Распределение рейтингов
    rating_distribution = {}
    for i in range(1, 6):
        rating_distribution[i] = reviews.filter(rating=i).count()
    
    context = {
        'product': product,
        'images': images,
        'specifications': specifications,
        'reviews': reviews,
        'related_products': related_products,
        'in_wishlist': in_wishlist,
        'in_compare': in_compare,
        'rating_stats': rating_stats,
        'rating_distribution': rating_distribution,
    }
    
    return render(request, 'catalog/product_detail.html', context)


def search_products(request):
    """
    Поиск товаров
    """
    query = request.GET.get('q', '').strip()
    products = Product.objects.none()
    
    if query:
        # Поиск по названию, описанию, артикулу, бренду, категории
        products = Product.objects.filter(
            Q(is_active=True) & (
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(sku__icontains=query) |
                Q(brand__name__icontains=query) |
                Q(category__name__icontains=query)
            )
        ).select_related('category', 'brand').prefetch_related('images')
        
        # Сортировка по релевантности
        if query.lower() in products[0].name.lower() if products.exists() else False:
            products = products.order_by('name')
        else:
            products = products.order_by('-views_count')
        
        # Сохраняем поисковый запрос
        if request.user.is_authenticated:
            from core.models import SearchLog
            SearchLog.objects.create(
                user=request.user,
                query=query,
                results_count=products.count()
            )
    
    # Пагинация
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'query': query,
        'page_obj': page_obj,
        'total_results': products.count() if query else 0,
    }
    
    return render(request, 'catalog/search_results.html', context)


@require_http_methods(["GET"])
def search_suggestions(request):
    """
    AJAX поиск с автодополнением
    """
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    # Кэшируем результаты поиска
    cache_key = f'search_suggestions_{query.lower()}'
    suggestions = cache.get(cache_key)
    
    if suggestions is None:
        # Ищем товары, бренды и категории
        product_suggestions = list(Product.objects.filter(
            is_active=True,
            name__istartswith=query
        )[:5].values('slug', 'name'))
        
        brand_suggestions = list(Brand.objects.filter(
            is_active=True,
            name__istartswith=query
        )[:3].values('slug', 'name'))
        
        category_suggestions = list(Category.objects.filter(
            is_active=True,
            name__istartswith=query
        )[:3].values('slug', 'name'))
        
        suggestions = {
            'products': product_suggestions,
            'brands': brand_suggestions,
            'categories': category_suggestions,
        }
        
        cache.set(cache_key, suggestions, 300)  # Кэшируем на 5 минут
    
    return JsonResponse(suggestions)


@require_http_methods(["GET"])
def filter_products(request):
    """
    AJAX фильтрация товаров
    """
    # Получаем параметры фильтрации
    category_id = request.GET.get('category')
    brand_id = request.GET.get('brand')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    in_stock = request.GET.get('in_stock')
    
    query = Product.objects.filter(is_active=True)
    
    if category_id:
        query = query.filter(category_id=category_id)
    if brand_id:
        query = query.filter(brand_id=brand_id)
    if min_price:
        query = query.filter(price__gte=min_price)
    if max_price:
        query = query.filter(price__lte=max_price)
    if in_stock:
        query = query.filter(in_stock=True)
    
    # Сортировка
    sort_by = request.GET.get('sort', 'name')
    sort_options = {
        'name': 'name',
        'price': 'price',
        'rating': 'rating',
        'newest': '-created_at',
        'popularity': '-sales_count',
    }
    
    sort_field = sort_options.get(sort_by, 'name')
    query = query.order_by(sort_field)
    
    # Пагинация
    paginator = Paginator(query.select_related('category', 'brand').prefetch_related('images'), 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Формируем ответ
    products_data = []
    for product in page_obj:
        products_data.append({
            'id': product.id,
            'slug': product.slug,
            'name': product.name,
            'brand': product.brand.name,
            'category': product.category.name,
            'price': str(product.price),
            'old_price': str(product.old_price) if product.old_price else None,
            'image': product.get_main_image().url if product.get_main_image() else None,
            'in_stock': product.in_stock,
            'rating': str(product.rating),
            'reviews_count': product.reviews_count,
            'discount_percent': product.get_discount_percent(),
        })
    
    response_data = {
        'products': products_data,
        'total_pages': paginator.num_pages,
        'current_page': page_obj.number,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'total_products': paginator.count,
    }
    
    return JsonResponse(response_data)


@require_http_methods(["GET"])
def api_product_quick_view(request, slug):
    """
    AJAX быстрый просмотр товара
    """
    try:
        product = Product.objects.get(slug=slug, is_active=True)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    
    product_data = {
        'id': product.id,
        'slug': product.slug,
        'name': product.name,
        'brand': product.brand.name,
        'price': str(product.price),
        'old_price': str(product.old_price) if product.old_price else None,
        'main_image': product.get_main_image().url if product.get_main_image() else None,
        'images': [img.image.url for img in product.get_all_images()[:4]],
        'in_stock': product.in_stock,
        'short_description': product.short_description,
        'rating': str(product.rating),
        'reviews_count': product.reviews_count,
        'discount_percent': product.get_discount_percent(),
    }
    
    return JsonResponse({'product': product_data})


@login_required
def wishlist(request):
    """
    Избранные товары пользователя
    """
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    
    # Пагинация
    paginator = Paginator(wishlist_items, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_items': wishlist_items.count(),
    }
    
    return render(request, 'catalog/wishlist.html', context)


@login_required
@require_http_methods(["POST"])
def add_to_wishlist(request, product_slug):
    """
    Добавление товара в избранное
    """
    try:
        product = Product.objects.get(slug=product_slug, is_active=True)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    if created:
        return JsonResponse({
            'status': 'added',
            'message': 'Товар добавлен в избранное',
            'total_wishlist': Wishlist.objects.filter(user=request.user).count()
        })
    else:
        return JsonResponse({
            'status': 'exists',
            'message': 'Товар уже в избранном',
        })


@login_required
@require_http_methods(["POST"])
def remove_from_wishlist(request, product_slug):
    """
    Удаление товара из избранного
    """
    try:
        product = Product.objects.get(slug=product_slug, is_active=True)
        Wishlist.objects.filter(user=request.user, product=product).delete()
        
        return JsonResponse({
            'status': 'removed',
            'message': 'Товар удален из избранного',
            'total_wishlist': Wishlist.objects.filter(user=request.user).count()
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)


@login_required
def compare_products(request):
    """
    Список товаров для сравнения
    """
    compare_items = CompareList.objects.filter(user=request.user).select_related('product')
    
    context = {
        'compare_items': compare_items,
        'total_items': compare_items.count(),
    }
    
    return render(request, 'catalog/compare.html', context)


@login_required
@require_http_methods(["POST"])
def add_to_compare(request, product_slug):
    """
    Добавление товара в сравнение
    """
    try:
        product = Product.objects.get(slug=product_slug, is_active=True)
        
        # Проверяем лимит сравнения (максимум 4 товара)
        current_count = CompareList.objects.filter(user=request.user).count()
        if current_count >= 4:
            return JsonResponse({
                'error': 'Максимум можно сравнивать 4 товара',
                'max_limit': 4
            })
        
        compare_item, created = CompareList.objects.get_or_create(
            user=request.user,
            product=product
        )
        
        if created:
            return JsonResponse({
                'status': 'added',
                'message': 'Товар добавлен в сравнение',
                'total_compare': CompareList.objects.filter(user=request.user).count()
            })
        else:
            return JsonResponse({
                'status': 'exists',
                'message': 'Товар уже в сравнении',
            })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)


@login_required
@require_http_methods(["POST"])
def remove_from_compare(request, product_slug):
    """
    Удаление товара из сравнения
    """
    try:
        product = Product.objects.get(slug=product_slug, is_active=True)
        CompareList.objects.filter(user=request.user, product=product).delete()
        
        return JsonResponse({
            'status': 'removed',
            'message': 'Товар удален из сравнения',
            'total_compare': CompareList.objects.filter(user=request.user).count()
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)


@login_required
@require_http_methods(["GET"])
def recently_viewed(request):
    """
    Недавно просмотренные товары
    """
    recently_viewed = RecentlyViewed.objects.filter(
        user=request.user
    ).select_related('product').order_by('-viewed_at')[:20]
    
    context = {
        'recently_viewed': recently_viewed,
    }
    
    return render(request, 'catalog/recently_viewed.html', context)


# Placeholder views для других функций
def category_list(request):
    """Список всех категорий"""
    categories = Category.objects.filter(is_active=True)
    return render(request, 'catalog/category_list.html', {'categories': categories})


def brand_list(request):
    """Список всех брендов"""
    brands = Brand.objects.filter(is_active=True)
    return render(request, 'catalog/brand_list.html', {'brands': brands})


def category_products(request, slug):
    """Товары категории"""
    return category_detail(request, slug)


def brand_products(request, slug):
    """Товары бренда"""
    return brand_detail(request, slug)


def product_images(request, slug):
    """Изображения товара"""
    return product_detail(request, slug)


def product_reviews(request, slug):
    """Отзывы о товаре"""
    return product_detail(request, slug)


def product_specifications(request, slug):
    """Характеристики товара"""
    return product_detail(request, slug)


def related_products(request, slug):
    """Похожие товары"""
    return product_detail(request, slug)


def product_availability(request, slug):
    """Наличие товара"""
    return JsonResponse({'status': 'success'})


def review_list(request):
    """Список отзывов"""
    return render(request, 'catalog/review_list.html')


def add_review(request):
    """Добавление отзыва"""
    return redirect('catalog:product_list')


def edit_review(request, review_id):
    """Редактирование отзыва"""
    return redirect('catalog:product_list')


def delete_review(request, review_id):
    """Удаление отзыва"""
    return redirect('catalog:product_list')


def mark_review_helpful(request, review_id):
    """Отметка отзыва как полезного"""
    return JsonResponse({'status': 'success'})


def popular_searches(request):
    """Популярные поисковые запросы"""
    return JsonResponse({'searches': []})


def filter_by_categories(request):
    """Фильтр по категориям"""
    return filter_products(request)


def filter_by_brands(request):
    """Фильтр по брендам"""
    return filter_products(request)


def filter_by_price(request):
    """Фильтр по цене"""
    return filter_products(request)


def filter_by_specifications(request):
    """Фильтр по характеристикам"""
    return filter_products(request)


def filter_by_availability(request):
    """Фильтр по наличию"""
    return filter_products(request)


def sort_products(request):
    """Сортировка товаров"""
    return filter_products(request)


def sort_by_price(request):
    """Сортировка по цене"""
    return sort_products(request)


def sort_by_popularity(request):
    """Сортировка по популярности"""
    return sort_products(request)


def sort_by_newest(request):
    """Сортировка по новизне"""
    return sort_products(request)


def sort_by_rating(request):
    """Сортировка по рейтингу"""
    return sort_products(request)


def clear_wishlist(request):
    """Очистка избранного"""
    if request.user.is_authenticated:
        Wishlist.objects.filter(user=request.user).delete()
        messages.success(request, 'Избранное очищено')
    return redirect('catalog:wishlist')


def clear_compare_list(request):
    """Очистка сравнения"""
    if request.user.is_authenticated:
        CompareList.objects.filter(user=request.user).delete()
        messages.success(request, 'Список сравнения очищен')
    return redirect('catalog:compare_products')


def specification_list(request):
    """Список характеристик"""
    specifications = ProductSpecification.objects.all()
    return render(request, 'catalog/specification_list.html', {'specifications': specifications})


def specification_detail(request, slug):
    """Детальная страница характеристики"""
    return render(request, 'catalog/specification_detail.html')


def product_statistics(request):
    """Статистика товаров"""
    return render(request, 'catalog/product_statistics.html')


def trending_products(request):
    """Популярные товары"""
    products = Product.objects.filter(is_active=True).order_by('-views_count')[:20]
    return render(request, 'catalog/trending_products.html', {'products': products})


def bestsellers(request):
    """Хиты продаж"""
    products = Product.objects.filter(is_active=True).order_by('-sales_count')[:20]
    return render(request, 'catalog/bestsellers.html', {'products': products})


def new_arrivals(request):
    """Новинки"""
    products = Product.objects.filter(is_active=True).order_by('-created_at')[:20]
    return render(request, 'catalog/new_arrivals.html', {'products': products})


def on_sale_products(request):
    """Товары со скидкой"""
    products = Product.objects.filter(is_active=True, old_price__isnull=False).order_by('-created_at')[:20]
    return render(request, 'catalog/on_sale_products.html', {'products': products})


def promotions(request):
    """Акции"""
    return render(request, 'catalog/promotions.html')


def promotion_detail(request, slug):
    """Детальная страница акции"""
    return render(request, 'catalog/promotion_detail.html')


def discounts(request):
    """Скидки"""
    return render(request, 'catalog/discounts.html')


def discount_detail(request, slug):
    """Детальная страница скидки"""
    return render(request, 'catalog/discount_detail.html')


def tag_list(request):
    """Список тегов"""
    return render(request, 'catalog/tag_list.html')


def tag_products(request, slug):
    """Товары по тегу"""
    return render(request, 'catalog/tag_products.html')


def recommendations(request):
    """Рекомендации"""
    return render(request, 'catalog/recommendations.html')


def personal_recommendations(request):
    """Персональные рекомендации"""
    return render(request, 'catalog/personal_recommendations.html')


def similar_products(request, product_slug):
    """Похожие товары"""
    return render(request, 'catalog/similar_products.html')


def bought_together(request, product_slug):
    """Товары, которые покупают вместе"""
    return render(request, 'catalog/bought_together.html')


def saved_products(request):
    """Отложенные товары"""
    return render(request, 'catalog/saved_products.html')


def add_to_saved(request, product_slug):
    """Добавить в отложенные"""
    return JsonResponse({'status': 'added'})


def remove_from_saved(request, product_slug):
    """Удалить из отложенных"""
    return JsonResponse({'status': 'removed'})


def compare_by_specifications(request):
    """Сравнение по характеристикам"""
    return render(request, 'catalog/compare_by_specifications.html')


def export_catalog_csv(request):
    """Экспорт каталога в CSV"""
    return HttpResponse('Export not implemented')


def export_catalog_excel(request):
    """Экспорт каталога в Excel"""
    return HttpResponse('Export not implemented')


def export_catalog_xml(request):
    """Экспорт каталога в XML"""
    return HttpResponse('Export not implemented')


def import_products(request):
    """Импорт товаров"""
    return render(request, 'catalog/import_products.html')


def api_product_availability(request, slug):
    """API доступности товара"""
    return JsonResponse({'available': True})


def api_add_to_cart(request, slug):
    """API добавления в корзину"""
    return JsonResponse({'status': 'added'})


def api_add_to_wishlist(request, slug):
    """API добавления в избранное"""
    return JsonResponse({'status': 'added'})


def api_add_to_compare(request, slug):
    """API добавления в сравнение"""
    return JsonResponse({'status': 'added'})


def api_remove_from_wishlist(request, slug):
    """API удаления из избранного"""
    return JsonResponse({'status': 'removed'})


def api_remove_from_compare(request, slug):
    """API удаления из сравнения"""
    return JsonResponse({'status': 'removed'})


def api_product_list(request):
    """API список товаров"""
    return JsonResponse({'products': []})


def api_product_detail(request, slug):
    """API детали товара"""
    return JsonResponse({'product': {}})


def api_category_list(request):
    """API список категорий"""
    return JsonResponse({'categories': []})


def api_brand_list(request):
    """API список брендов"""
    return JsonResponse({'brands': []})


def api_search(request):
    """API поиск"""
    return JsonResponse({'results': []})


def api_filter(request):
    """API фильтрация"""
    return JsonResponse({'filtered': []})


def api_sort(request):
    """API сортировка"""
    return JsonResponse({'sorted': []})


def api_review_list(request):
    """API список отзывов"""
    return JsonResponse({'reviews': []})


def api_add_review(request):
    """API добавление отзыва"""
    return JsonResponse({'status': 'added'})


def yandex_market_feed(request):
    """Feed для Яндекс.Маркет"""
    return HttpResponse('Feed not implemented')


def ozon_feed(request):
    """Feed для Ozon"""
    return HttpResponse('Feed not implemented')


def wildberries_feed(request):
    """Feed для Wildberries"""
    return HttpResponse('Feed not implemented')


def product_sitemap(request):
    """Sitemap товаров"""
    return HttpResponse('Sitemap not implemented')


def category_sitemap(request):
    """Sitemap категорий"""
    return HttpResponse('Sitemap not implemented')


def brand_sitemap(request):
    """Sitemap брендов"""
    return HttpResponse('Sitemap not implemented')


def spa_catalog(request, path):
    """SPA роутер для каталога"""
    return render(request, 'catalog/spa_catalog.html')
