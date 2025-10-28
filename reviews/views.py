"""
Представления для системы отзывов и рейтингов
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.conf import settings
from django.core.cache import cache
from django.db import transaction, models
from django.db.models import Q, Avg, Count
from django.utils import timezone
from django.core.paginator import Paginator
from decimal import Decimal
import json
from datetime import datetime, date

from catalog.models import Product
from accounts.models import User
from .models import Review, ReviewHelpfulness, ReviewPhoto, ReviewVideo, ReviewFlag
from .forms import ReviewForm, ReviewHelpfulnessForm, ReviewFilterForm, ReviewSearchForm


@login_required
@require_http_methods(["GET", "POST"])
def product_reviews(request, product_id):
    """
    Список отзывов о товаре
    """
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    # Получаем отзывы с фильтрацией
    reviews = Review.objects.filter(
        product=product,
        is_approved=True
    ).select_related('user').prefetch_related(
        'reviewhelpfulness_set',
        'reviewphoto_set',
        'reviewvideo_set'
    )
    
    # Фильтрация отзывов
    form = ReviewFilterForm(request.GET)
    if form.is_valid():
        rating = form.cleaned_data.get('rating')
        has_photos = form.cleaned_data.get('has_photos')
        has_videos = form.cleaned_data.get('has_videos')
        verified_only = form.cleaned_data.get('verified_only')
        sort_by = form.cleaned_data.get('sort_by')
        
        if rating:
            reviews = reviews.filter(rating=rating)
        if has_photos:
            reviews = reviews.filter(reviewphoto__isnull=False).distinct()
        if has_videos:
            reviews = reviews.filter(reviewvideo__isnull=False).distinct()
        if verified_only:
            reviews = reviews.filter(is_verified_purchase=True)
        
        if sort_by:
            reviews = reviews.order_by(sort_by)
        else:
            reviews = reviews.order_by('-created_at')
    else:
        reviews = reviews.order_by('-created_at')
    
    # Статистика отзывов
    review_stats = get_review_statistics(product)
    
    # Рекомендации на основе отзывов
    recommendations = get_review_based_recommendations(product)
    
    # Форма добавления отзыва
    review_form = None
    can_add_review = False
    
    if request.user.is_authenticated:
        # Проверяем, можно ли добавить отзыв
        can_add_review = can_user_add_review(request.user, product)
        
        if request.method == 'POST' and can_add_review:
            review_form = ReviewForm(request.POST, request.FILES, product=product, user=request.user)
            if review_form.is_valid():
                try:
                    with transaction.atomic():
                        review = review_form.save()
                        messages.success(request, 'Отзыв успешно добавлен и ожидает модерации')
                        return redirect('reviews:product_reviews', product_id=product.id)
                except Exception as e:
                    messages.error(request, f'Ошибка при добавлении отзыва: {str(e)}')
        else:
            review_form = ReviewForm(product=product, user=request.user)
    
    # AJAX пагинация
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        paginator = Paginator(reviews, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        reviews_data = []
        for review in page_obj.object_list:
            reviews_data.append({
                'id': review.id,
                'user_name': review.user.get_full_name(),
                'rating': review.rating,
                'title': review.title,
                'text': review.text[:200] + '...' if len(review.text) > 200 else review.text,
                'pros': review.pros,
                'cons': review.cons,
                'created_at': review.created_at.isoformat(),
                'helpful_count': review.helpful_count,
                'unhelpful_count': review.unhelpful_count,
                'photos_count': review.reviewphoto_set.count(),
                'videos_count': review.reviewvideo_set.count(),
                'is_verified_purchase': review.is_verified_purchase
            })
        
        return JsonResponse({
            'reviews': reviews_data,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages
        })
    
    # Обычная пагинация
    paginator = Paginator(reviews, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'product': product,
        'page_obj': page_obj,
        'reviews': page_obj.object_list,
        'review_stats': review_stats,
        'recommendations': recommendations,
        'review_form': review_form,
        'can_add_review': can_add_review,
        'filter_form': form,
        'user_review': get_user_review(request.user, product) if request.user.is_authenticated else None
    }
    
    return render(request, 'reviews/product_reviews.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def add_review(request, product_id):
    """
    Добавление отзыва о товаре
    """
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    # Проверяем права на добавление отзыва
    if not can_user_add_review(request.user, product):
        messages.error(request, 'Вы не можете оставить отзыв об этом товаре')
        return redirect('catalog:product_detail', slug=product.slug)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES, product=product, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    review = form.save()
                    
                    # Обновляем рейтинг товара
                    update_product_rating(product)
                    
                    messages.success(request, 'Отзыв успешно добавлен и ожидает модерации')
                    return redirect('reviews:product_reviews', product_id=product.id)
                    
            except Exception as e:
                messages.error(request, f'Ошибка при добавлении отзыва: {str(e)}')
    else:
        form = ReviewForm(product=product, user=request.user)
    
    context = {
        'product': product,
        'form': form
    }
    
    return render(request, 'reviews/add_review.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def edit_review(request, review_id):
    """
    Редактирование отзыва
    """
    review = get_object_or_404(Review, id=review_id, user=request.user)
    product = review.product
    
    if not review.can_edit():
        messages.error(request, 'Вы не можете редактировать этот отзыв')
        return redirect('reviews:product_reviews', product_id=product.id)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES, instance=review, product=product, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    review = form.save()
                    review.is_approved = False  # Требуется повторная модерация
                    review.save()
                    
                    messages.success(request, 'Отзыв обновлен и ожидает модерации')
                    return redirect('reviews:product_reviews', product_id=product.id)
                    
            except Exception as e:
                messages.error(request, f'Ошибка при обновлении отзыва: {str(e)}')
    else:
        form = ReviewForm(instance=review, product=product, user=request.user)
    
    context = {
        'product': product,
        'review': review,
        'form': form
    }
    
    return render(request, 'reviews/edit_review.html', context)


@login_required
@require_http_methods(["POST"])
def delete_review(request, review_id):
    """
    Удаление отзыва
    """
    review = get_object_or_404(Review, id=review_id, user=request.user)
    product = review.product
    
    if not review.can_edit():
        return JsonResponse({'error': 'Вы не можете удалить этот отзыв'}, status=403)
    
    try:
        with transaction.atomic():
            review.delete()
            
            # Обновляем рейтинг товара
            update_product_rating(product)
            
            messages.success(request, 'Отзыв удален')
            
    except Exception as e:
        messages.error(request, f'Ошибка при удалении отзыва: {str(e)}')
    
    return redirect('reviews:product_reviews', product_id=product.id)


@login_required
@require_http_methods(["POST"])
def vote_review_helpfulness(request, review_id):
    """
    Голосование за полезность отзыва
    """
    review = get_object_or_404(Review, id=review_id, is_approved=True)
    
    try:
        data = json.loads(request.body)
        is_helpful = data.get('is_helpful')
        
        # Проверяем, не голосовал ли уже пользователь
        existing_vote = ReviewHelpfulness.objects.filter(
            review=review,
            user=request.user
        ).first()
        
        if existing_vote:
            # Если голос уже есть, обновляем его
            old_vote = existing_vote.is_helpful
            existing_vote.is_helpful = is_helpful
            existing_vote.save()
            
            # Обновляем счетчики полезности
            if old_vote != is_helpful:
                if is_helpful:
                    review.helpful_count += 1
                    review.unhelpful_count -= 1 if old_vote else 0
                else:
                    review.unhelpful_count += 1
                    review.helpful_count -= 1 if not old_vote else 0
                review.save()
        else:
            # Создаем новый голос
            ReviewHelpfulness.objects.create(
                review=review,
                user=request.user,
                is_helpful=is_helpful
            )
            
            # Обновляем счетчики
            if is_helpful:
                review.helpful_count += 1
            else:
                review.unhelpful_count += 1
            review.save()
        
        return JsonResponse({
            'status': 'success',
            'helpful_count': review.helpful_count,
            'unhelpful_count': review.unhelpful_count,
            'message': 'Ваш голос учтен'
        })
        
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Неверный запрос'}, status=400)


@login_required
@require_http_methods(["POST"])
def flag_review(request, review_id):
    """
    Жалоба на отзыв
    """
    review = get_object_or_404(Review, id=review_id, is_approved=True)
    
    try:
        data = json.loads(request.body)
        flag_reason = data.get('reason')
        flag_text = data.get('reason_text', '')
        
        # Проверяем, не жаловался ли уже пользователь
        existing_flag = ReviewFlag.objects.filter(
            review=review,
            user=request.user
        ).first()
        
        if existing_flag:
            return JsonResponse({
                'error': 'Вы уже подали жалобу на этот отзыв'
            }, status=400)
        
        # Создаем жалобу
        ReviewFlag.objects.create(
            review=review,
            user=request.user,
            reason=flag_reason,
            reason_text=flag_text
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Жалоба отправлена модераторам'
        })
        
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Неверный запрос'}, status=400)


@login_required
@require_http_methods(["GET"])
def my_reviews(request):
    """
    Мои отзывы (личный кабинет)
    """
    reviews = Review.objects.filter(
        user=request.user
    ).select_related('product').prefetch_related(
        'reviewphoto_set',
        'reviewvideo_set'
    ).order_by('-created_at')
    
    # Фильтрация
    status_filter = request.GET.get('status')
    if status_filter == 'approved':
        reviews = reviews.filter(is_approved=True)
    elif status_filter == 'pending':
        reviews = reviews.filter(is_approved=False)
    elif status_filter == 'rejected':
        reviews = reviews.filter(is_rejected=True)
    
    # Поиск
    search_query = request.GET.get('q')
    if search_query:
        reviews = reviews.filter(
            Q(title__icontains=search_query) |
            Q(text__icontains=search_query) |
            Q(product__name__icontains=search_query)
        )
    
    # Пагинация
    paginator = Paginator(reviews, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'reviews': page_obj.object_list,
        'status_filter': status_filter,
        'search_query': search_query,
        'review_stats': {
            'total': reviews.count(),
            'approved': Review.objects.filter(user=request.user, is_approved=True).count(),
            'pending': Review.objects.filter(user=request.user, is_approved=False).count(),
        }
    }
    
    return render(request, 'reviews/my_reviews.html', context)


@login_required
@require_http_methods(["GET"])
def review_detail(request, review_id):
    """
    Детальная страница отзыва
    """
    review = get_object_or_404(
        Review.objects.select_related('product', 'user'),
        id=review_id,
        is_approved=True
    )
    
    # Проверяем права доступа
    if review.user != request.user and not request.user.is_staff:
        # Обычные пользователи видят только одобренные отзывы
        pass
    
    context = {
        'review': review,
        'product': review.product,
        'user_vote': get_user_vote(request.user, review) if request.user.is_authenticated else None,
        'user_flag': get_user_flag(request.user, review) if request.user.is_authenticated else None,
        'related_reviews': get_related_reviews(review),
        'helpful_votes': ReviewHelpfulness.objects.filter(review=review, is_helpful=True).select_related('user'),
    }
    
    return render(request, 'reviews/review_detail.html', context)


@require_http_methods(["GET"])
def product_reviews_summary(request, product_id):
    """
    Краткая сводка отзывов о товаре (AJAX)
    """
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    stats = get_review_statistics(product)
    recent_reviews = Review.objects.filter(
        product=product,
        is_approved=True
    ).select_related('user')[:5]
    
    reviews_data = []
    for review in recent_reviews:
        reviews_data.append({
            'id': review.id,
            'user_name': review.user.get_full_name(),
            'rating': review.rating,
            'title': review.title[:100] + '...' if len(review.title) > 100 else review.title,
            'created_at': review.created_at.isoformat(),
            'is_verified_purchase': review.is_verified_purchase
        })
    
    return JsonResponse({
        'total_reviews': stats['total_reviews'],
        'average_rating': str(stats['average_rating']),
        'rating_distribution': stats['rating_distribution'],
        'recent_reviews': reviews_data,
        'has_photos': stats['has_photos'],
        'has_videos': stats['has_videos'],
        'verified_purchase_percent': stats['verified_purchase_percent']
    })


@login_required
@require_http_methods(["GET"])
def user_review_history(request, user_id):
    """
    История отзывов пользователя (для администраторов)
    """
    target_user = get_object_or_404(User, id=user_id)
    
    reviews = Review.objects.filter(
        user=target_user
    ).select_related('product').order_by('-created_at')
    
    context = {
        'target_user': target_user,
        'reviews': reviews,
        'total_reviews': reviews.count(),
        'average_rating': reviews.aggregate(avg=models.Avg('rating'))['avg'] or 0
    }
    
    return render(request, 'reviews/user_review_history.html', context)


@login_required
@require_http_methods(["GET"])
def reviews_analytics(request):
    """
    Аналитика отзывов (для администраторов)
    """
    # Общая статистика
    total_reviews = Review.objects.filter(is_approved=True).count()
    total_products_with_reviews = Review.objects.filter(
        is_approved=True
    ).values('product').distinct().count()
    
    # Статистика по рейтингам
    rating_stats = Review.objects.filter(is_approved=True).values('rating').annotate(
        count=models.Count('id')
    ).order_by('rating')
    
    # Статистика модерации
    moderation_stats = {
        'pending': Review.objects.filter(is_approved=False, is_rejected=False).count(),
        'approved': Review.objects.filter(is_approved=True).count(),
        'rejected': Review.objects.filter(is_rejected=True).count(),
    }
    
    # Топ товары с отзывами
    top_rated_products = Product.objects.filter(
        reviews__is_approved=True
    ).annotate(
        review_count=models.Count('reviews'),
        avg_rating=models.Avg('reviews__rating')
    ).filter(review_count__gt=0).order_by('-avg_rating', '-review_count')[:10]
    
    # Активность по времени
    from django.utils import timezone
    last_month = timezone.now() - timezone.timedelta(days=30)
    monthly_reviews = Review.objects.filter(
        created_at__gte=last_month,
        is_approved=True
    ).extra(
        select={'date': 'DATE(created_at)'}
    ).values('date').annotate(
        count=models.Count('id')
    ).order_by('date')
    
    context = {
        'total_reviews': total_reviews,
        'total_products_with_reviews': total_products_with_reviews,
        'rating_stats': rating_stats,
        'moderation_stats': moderation_stats,
        'top_rated_products': top_rated_products,
        'monthly_reviews': monthly_reviews,
    }
    
    return render(request, 'reviews/reviews_analytics.html', context)


@login_required
@require_http_methods(["GET"])
def review_search(request):
    """
    Поиск отзывов (для администраторов)
    """
    form = ReviewSearchForm(request.GET)
    reviews = Review.objects.all()
    
    if form.is_valid():
        search_query = form.cleaned_data.get('search_query')
        product_name = form.cleaned_data.get('product_name')
        user_name = form.cleaned_data.get('user_name')
        rating = form.cleaned_data.get('rating')
        status = form.cleaned_data.get('status')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        has_photos = form.cleaned_data.get('has_photos')
        verified_only = form.cleaned_data.get('verified_only')
        
        if search_query:
            reviews = reviews.filter(
                Q(title__icontains=search_query) |
                Q(text__icontains=search_query) |
                Q(pros__icontains=search_query) |
                Q(cons__icontains=search_query)
            )
        if product_name:
            reviews = reviews.filter(product__name__icontains=product_name)
        if user_name:
            reviews = reviews.filter(
                Q(user__first_name__icontains=user_name) |
                Q(user__last_name__icontains=user_name) |
                Q(user__username__icontains=user_name)
            )
        if rating:
            reviews = reviews.filter(rating=rating)
        if status == 'approved':
            reviews = reviews.filter(is_approved=True)
        elif status == 'pending':
            reviews = reviews.filter(is_approved=False, is_rejected=False)
        elif status == 'rejected':
            reviews = reviews.filter(is_rejected=True)
        if date_from:
            reviews = reviews.filter(created_at__date__gte=date_from)
        if date_to:
            reviews = reviews.filter(created_at__date__lte=date_to)
        if has_photos:
            reviews = reviews.filter(reviewphoto__isnull=False).distinct()
        if verified_only:
            reviews = reviews.filter(is_verified_purchase=True)
    
    # Пагинация
    paginator = Paginator(reviews.select_related('product', 'user').prefetch_related('reviewphoto_set'), 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'reviews': page_obj.object_list,
        'results_count': reviews.count()
    }
    
    return render(request, 'reviews/review_search.html', context)


# Вспомогательные функции

def can_user_add_review(user, product):
    """
    Проверяет, может ли пользователь оставить отзыв
    """
    if not user.is_authenticated:
        return False
    
    # Проверяем, нет ли уже отзыва
    existing_review = Review.objects.filter(user=user, product=product).first()
    if existing_review:
        return False
    
    # Проверяем, покупал ли пользователь товар
    from orders.models import Order, OrderItem
    has_purchased = OrderItem.objects.filter(
        order__user=user,
        order__status='completed',
        product=product
    ).exists()
    
    return has_purchased


def get_user_review(user, product):
    """
    Получает отзыв пользователя о товаре
    """
    return Review.objects.filter(user=user, product=product).first()


def update_product_rating(product):
    """
    Обновляет рейтинг товара на основе отзывов
    """
    reviews = Review.objects.filter(product=product, is_approved=True)
    
    if reviews.exists():
        avg_rating = reviews.aggregate(avg=models.Avg('rating'))['avg']
        product.rating = round(avg_rating, 1)
        product.reviews_count = reviews.count()
    else:
        product.rating = 0
        product.reviews_count = 0
    
    product.save(update_fields=['rating', 'reviews_count'])


def get_review_statistics(product):
    """
    Получает статистику отзывов товара
    """
    reviews = Review.objects.filter(product=product, is_approved=True)
    
    if not reviews.exists():
        return {
            'total_reviews': 0,
            'average_rating': 0,
            'rating_distribution': {i: 0 for i in range(1, 6)},
            'has_photos': 0,
            'has_videos': 0,
            'verified_purchase_percent': 0
        }
    
    total_reviews = reviews.count()
    average_rating = reviews.aggregate(avg=models.Avg('rating'))['avg'] or 0
    
    # Распределение по рейтингам
    rating_distribution = {}
    for i in range(1, 6):
        rating_distribution[i] = reviews.filter(rating=i).count()
    
    # Статистика медиа
    has_photos = reviews.filter(reviewphoto__isnull=False).distinct().count()
    has_videos = reviews.filter(reviewvideo__isnull=False).distinct().count()
    
    # Процент проверенных покупок
    verified_count = reviews.filter(is_verified_purchase=True).count()
    verified_purchase_percent = round((verified_count / total_reviews) * 100, 1)
    
    return {
        'total_reviews': total_reviews,
        'average_rating': round(average_rating, 1),
        'rating_distribution': rating_distribution,
        'has_photos': has_photos,
        'has_videos': has_videos,
        'verified_purchase_percent': verified_purchase_percent
    }


def get_review_based_recommendations(product):
    """
    Рекомендации на основе отзывов
    """
    # Получаем схожие товары по категории
    similar_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id)[:4]
    
    recommendations = []
    for similar_product in similar_products:
        stats = get_review_statistics(similar_product)
        if stats['total_reviews'] > 0 and stats['average_rating'] >= 4:
            recommendations.append(similar_product)
    
    return recommendations


def get_user_vote(user, review):
    """
    Получает голос пользователя за отзыв
    """
    if not user.is_authenticated:
        return None
    
    return ReviewHelpfulness.objects.filter(review=review, user=user).first()


def get_user_flag(user, review):
    """
    Получает жалобу пользователя на отзыв
    """
    if not user.is_authenticated:
        return None
    
    return ReviewFlag.objects.filter(review=review, user=user).first()


def get_related_reviews(review):
    """
    Получает связанные отзывы
    """
    return Review.objects.filter(
        product__category=review.product.category,
        is_approved=True
    ).exclude(id=review.id).order_by('-rating', '-helpful_count')[:5]