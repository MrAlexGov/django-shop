"""
Представления для приложения accounts (пользователи и личный кабинет)
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
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from decimal import Decimal
import json
import csv
from datetime import datetime, date

from .models import User, UserProfile, Address, Wishlist, CompareList, DiscountCode, UserDiscount
from orders.models import Order, OrderItem
from catalog.models import Product, Review
from .forms import (
    ProfileUpdateForm, AddressForm, ChangePasswordForm, 
    NotificationSettingsForm, AccountSettingsForm, WishlistForm
)


@login_required
@require_http_methods(["GET", "POST"])
def dashboard(request):
    """
    Главная страница личного кабинета
    """
    user = request.user
    
    # Получаем статистику пользователя
    stats = get_user_dashboard_stats(user)
    
    # Последние заказы
    recent_orders = Order.objects.filter(user=user).select_related().prefetch_related('items')[:5]
    
    # Избранные товары
    wishlist_items = Wishlist.objects.filter(user=user).select_related('product')[:10]
    
    # Рекомендации
    recommendations = get_personalized_recommendations(user)
    
    # Уведомления
    notifications = get_user_notifications(user)[:5]
    
    context = {
        'user': user,
        'stats': stats,
        'recent_orders': recent_orders,
        'wishlist_items': wishlist_items,
        'recommendations': recommendations,
        'notifications': notifications
    }
    
    return render(request, 'accounts/dashboard.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def profile_update(request):
    """
    Редактирование профиля пользователя
    """
    user = request.user
    
    # Получаем или создаем профиль
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=user, profile=profile)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                profile = form.save_profile()
                messages.success(request, 'Профиль успешно обновлен')
                return redirect('accounts:profile_update')
    else:
        form = ProfileUpdateForm(instance=user, profile=profile)
    
    context = {
        'form': form,
        'user': user,
        'profile': profile
    }
    
    return render(request, 'accounts/profile_update.html', context)


@login_required
@require_http_methods(["GET"])
def addresses_list(request):
    """
    Список адресов пользователя
    """
    addresses = Address.objects.filter(user=request.user).order_by('-is_default', '-created_at')
    
    context = {
        'addresses': addresses,
        'addresses_count': addresses.count()
    }
    
    return render(request, 'accounts/addresses_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def address_create(request):
    """
    Создание нового адреса
    """
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            
            # Если это первый адрес, делаем его по умолчанию
            if not Address.objects.filter(user=request.user).exists():
                address.is_default = True
            
            address.save()
            messages.success(request, 'Адрес успешно создан')
            return redirect('accounts:addresses_list')
    else:
        form = AddressForm()
    
    context = {
        'form': form,
        'title': 'Создание адреса'
    }
    
    return render(request, 'accounts/address_form.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def address_update(request, address_id):
    """
    Редактирование адреса
    """
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, 'Адрес успешно обновлен')
            return redirect('accounts:addresses_list')
    else:
        form = AddressForm(instance=address)
    
    context = {
        'form': form,
        'address': address,
        'title': 'Редактирование адреса'
    }
    
    return render(request, 'accounts/address_form.html', context)


@login_required
@require_http_methods(["POST"])
def address_delete(request, address_id):
    """
    Удаление адреса
    """
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if address.is_default:
        messages.error(request, 'Нельзя удалить адрес по умолчанию')
        return redirect('accounts:addresses_list')
    
    address.delete()
    messages.success(request, 'Адрес удален')
    return redirect('accounts:addresses_list')


@login_required
@require_http_methods(["POST"])
def address_set_default(request, address_id):
    """
    Установка адреса по умолчанию
    """
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    # Убираем флаг по умолчанию у других адресов
    Address.objects.filter(user=request.user).update(is_default=False)
    
    # Устанавливаем новый адрес по умолчанию
    address.is_default = True
    address.save()
    
    messages.success(request, 'Адрес по умолчанию изменен')
    return redirect('accounts:addresses_list')


@login_required
@require_http_methods(["GET"])
def wishlist(request):
    """
    Список избранных товаров
    """
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product').order_by('-created_at')
    
    # Пагинация
    paginator = Paginator(wishlist_items, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'wishlist_items': page_obj.object_list,
        'page_obj': page_obj,
        'wishlist_count': wishlist_items.count()
    }
    
    return render(request, 'accounts/wishlist.html', context)


@login_required
@require_http_methods(["POST"])
def add_to_wishlist(request):
    """
    Добавление товара в избранное (AJAX)
    """
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        # Проверяем, не добавлен ли уже товар
        existing = Wishlist.objects.filter(user=request.user, product=product).first()
        if existing:
            return JsonResponse({
                'status': 'error',
                'message': 'Товар уже в избранном'
            })
        
        # Добавляем в избранное
        Wishlist.objects.create(user=request.user, product=product)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Товар добавлен в избранное'
        })
        
    except (Product.DoesNotExist, json.JSONDecodeError) as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def remove_from_wishlist(request):
    """
    Удаление товара из избранного (AJAX)
    """
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        
        wishlist_item = Wishlist.objects.filter(
            user=request.user, 
            product_id=product_id
        ).first()
        
        if not wishlist_item:
            return JsonResponse({
                'status': 'error',
                'message': 'Товар не найден в избранном'
            })
        
        wishlist_item.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Товар удален из избранного'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
@require_http_methods(["GET"])
def compare_list(request):
    """
    Список сравнения товаров
    """
    compare_items = CompareList.objects.filter(user=request.user).select_related('product').order_by('-created_at')
    
    context = {
        'compare_items': compare_items,
        'compare_count': compare_items.count()
    }
    
    return render(request, 'accounts/compare_list.html', context)


@login_required
@require_http_methods(["POST"])
def add_to_compare(request):
    """
    Добавление товара в список сравнения (AJAX)
    """
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        # Проверяем, не добавлен ли уже товар
        existing = CompareList.objects.filter(user=request.user, product=product).first()
        if existing:
            return JsonResponse({
                'status': 'error',
                'message': 'Товар уже в списке сравнения'
            })
        
        # Добавляем в список сравнения
        CompareList.objects.create(user=request.user, product=product)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Товар добавлен в сравнение'
        })
        
    except (Product.DoesNotExist, json.JSONDecodeError) as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def remove_from_compare(request):
    """
    Удаление товара из списка сравнения (AJAX)
    """
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        
        compare_item = CompareList.objects.filter(
            user=request.user, 
            product_id=product_id
        ).first()
        
        if not compare_item:
            return JsonResponse({
                'status': 'error',
                'message': 'Товар не найден в списке сравнения'
            })
        
        compare_item.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Товар удален из сравнения'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
@require_http_methods(["GET", "POST"])
def change_password(request):
    """
    Смена пароля
    """
    if request.method == 'POST':
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Пароль успешно изменен')
            return redirect('accounts:change_password')
    else:
        form = ChangePasswordForm(request.user)
    
    context = {
        'form': form
    }
    
    return render(request, 'accounts/change_password.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def notification_settings(request):
    """
    Настройки уведомлений
    """
    profile = request.user.profile
    
    if request.method == 'POST':
        form = NotificationSettingsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Настройки уведомлений сохранены')
            return redirect('accounts:notification_settings')
    else:
        form = NotificationSettingsForm(instance=profile)
    
    context = {
        'form': form
    }
    
    return render(request, 'accounts/notification_settings.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def account_settings(request):
    """
    Настройки аккаунта
    """
    user = request.user
    
    if request.method == 'POST':
        form = AccountSettingsForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Настройки аккаунта сохранены')
            return redirect('accounts:account_settings')
    else:
        form = AccountSettingsForm(instance=user)
    
    context = {
        'form': form,
        'user': user
    }
    
    return render(request, 'accounts/account_settings.html', context)


@login_required
@require_http_methods(["POST"])
def delete_account(request):
    """
    Удаление аккаунта пользователя
    """
    if not request.user.check_password(request.POST.get('password', '')):
        messages.error(request, 'Неверный пароль')
        return redirect('accounts:account_settings')
    
    user = request.user
    user.is_active = False
    user.save()
    
    # Удаляем сессию
    request.session.flush()
    
    messages.success(request, 'Аккаунт успешно удален')
    return redirect('home')


@login_required
@require_http_methods(["GET"])
def order_history(request):
    """
    История заказов пользователя
    """
    orders = Order.objects.filter(user=request.user).select_related().prefetch_related('items')
    
    # Фильтрация
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Поиск
    search_query = request.GET.get('q')
    if search_query:
        orders = orders.filter(order_number__icontains=search_query)
    
    # Период
    period = request.GET.get('period')
    if period:
        if period == 'week':
            week_ago = timezone.now() - timezone.timedelta(days=7)
            orders = orders.filter(created_at__gte=week_ago)
        elif period == 'month':
            month_ago = timezone.now() - timezone.timedelta(days=30)
            orders = orders.filter(created_at__gte=month_ago)
        elif period == 'year':
            year_ago = timezone.now() - timezone.timedelta(days=365)
            orders = orders.filter(created_at__gte=year_ago)
    
    # Пагинация
    paginator = Paginator(orders.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'orders': page_obj.object_list,
        'page_obj': page_obj,
        'status_choices': Order.STATUS_CHOICES,
        'current_status': status_filter,
        'search_query': search_query,
        'period': period
    }
    
    return render(request, 'accounts/order_history.html', context)


@login_required
@require_http_methods(["GET"])
def bonuses(request):
    """
    Бонусная программа
    """
    user = request.user
    
    # История начисления и списания бонусов
    bonus_transactions = get_bonus_transactions(user)
    
    # Рекомендации по бонусам
    bonus_recommendations = get_bonus_recommendations(user)
    
    # Доступные действия с бонусами
    bonus_actions = get_available_bonus_actions(user)
    
    context = {
        'user': user,
        'bonus_transactions': bonus_transactions[:20],  # Последние 20 операций
        'recommendations': bonus_recommendations,
        'actions': bonus_actions
    }
    
    return render(request, 'accounts/bonuses.html', context)


@login_required
@require_http_methods(["GET"])
def analytics(request):
    """
    Аналитика пользователя
    """
    user = request.user
    
    # Общая статистика
    total_orders = Order.objects.filter(user=user).count()
    total_spent = Order.objects.filter(user=user).aggregate(
        total=models.Sum('total_amount')
    )['total'] or Decimal('0.00')
    
    # Статистика по месяцам
    monthly_stats = get_monthly_spending_stats(user)
    
    # Топ категории товаров
    top_categories = get_user_top_categories(user)
    
    # Активность
    activity_stats = get_user_activity_stats(user)
    
    context = {
        'total_orders': total_orders,
        'total_spent': total_spent,
        'monthly_stats': monthly_stats,
        'top_categories': top_categories,
        'activity_stats': activity_stats
    }
    
    return render(request, 'accounts/analytics.html', context)


@login_required
@require_http_methods(["GET"])
def download_data(request):
    """
    Скачивание данных пользователя
    """
    user = request.user
    
    if request.method == 'POST':
        # Создаем архив с данными пользователя
        data_package = create_user_data_package(user)
        
        response = HttpResponse(data_package, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="user_data_{user.id}_{date.today()}.zip"'
        
        return response
    
    return render(request, 'accounts/download_data.html')


@login_required
@require_http_methods(["GET"])
def support(request):
    """
    Служба поддержки в личном кабинете
    """
    # Получаем тикеты поддержки пользователя
    support_tickets = get_user_support_tickets(request.user)
    
    # Часто задаваемые вопросы
    faqs = get_frequently_asked_questions()
    
    context = {
        'support_tickets': support_tickets,
        'faqs': faqs
    }
    
    return render(request, 'accounts/support.html', context)


@login_required
@require_http_methods(["GET"])
def loyalty_program(request):
    """
    Программа лояльности
    """
    user = request.user
    
    # Уровень лояльности
    loyalty_level = calculate_loyalty_level(user)
    
    # Преимущества уровня
    level_benefits = get_loyalty_level_benefits(loyalty_level)
    
    # Прогресс до следующего уровня
    next_level_progress = get_next_level_progress(user)
    
    # Доступные награды
    available_rewards = get_available_loyalty_rewards(user)
    
    context = {
        'user': user,
        'loyalty_level': loyalty_level,
        'level_benefits': level_benefits,
        'next_level_progress': next_level_progress,
        'available_rewards': available_rewards
    }
    
    return render(request, 'accounts/loyalty_program.html', context)


# AJAX эндпоинты

@login_required
@require_http_methods(["POST"])
def update_profile_ajax(request):
    """
    Обновление профиля через AJAX
    """
    try:
        data = json.loads(request.body)
        field = data.get('field')
        value = data.get('value')
        
        user = request.user
        
        if field == 'first_name':
            user.first_name = value
        elif field == 'last_name':
            user.last_name = value
        elif field == 'phone':
            user.phone = value
        elif field == 'date_of_birth':
            user.date_of_birth = value
        else:
            return JsonResponse({'error': 'Invalid field'}, status=400)
        
        user.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Профиль обновлен'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@login_required
@require_http_methods(["GET"])
def get_user_stats_ajax(request):
    """
    Получение статистики пользователя (AJAX)
    """
    stats = get_user_dashboard_stats(request.user)
    return JsonResponse(stats)


@login_required
@require_http_methods(["POST"])
def update_notification_preference(request):
    """
    Обновление предпочтений уведомлений
    """
    try:
        data = json.loads(request.body)
        notification_type = data.get('type')
        enabled = data.get('enabled')
        
        profile = request.user.profile
        
        if notification_type == 'email':
            profile.email_notifications = enabled
        elif notification_type == 'sms':
            profile.sms_notifications = enabled
        elif notification_type == 'push':
            profile.push_notifications = enabled
        else:
            return JsonResponse({'error': 'Invalid notification type'}, status=400)
        
        profile.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Настройки уведомлений обновлены'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


# Вспомогательные функции

def get_user_dashboard_stats(user):
    """Получение статистики для дашборда пользователя"""
    stats = {}
    
    # Статистика заказов
    orders = Order.objects.filter(user=user)
    stats['total_orders'] = orders.count()
    stats['pending_orders'] = orders.filter(status__in=['pending', 'processing']).count()
    stats['completed_orders'] = orders.filter(status='completed').count()
    
    # Финансовая статистика
    stats['total_spent'] = orders.aggregate(total=models.Sum('total_amount'))['total'] or Decimal('0.00')
    stats['average_order_value'] = stats['total_spent'] / stats['total_orders'] if stats['total_orders'] > 0 else 0
    
    # Бонусная статистика
    stats['bonus_points'] = user.bonus_points
    stats['bonus_points_earned'] = UserDiscount.objects.filter(user=user).aggregate(
        total=models.Sum('discount_amount')
    )['total'] or Decimal('0.00')
    
    # Активность
    wishlist_count = Wishlist.objects.filter(user=user).count()
    compare_count = CompareList.objects.filter(user=user).count()
    stats['wishlist_count'] = wishlist_count
    stats['compare_count'] = compare_count
    
    return stats


def get_personalized_recommendations(user):
    """Получение персональных рекомендаций"""
    if not user.is_authenticated:
        return Product.objects.filter(is_active=True, is_featured=True)[:6]
    
    # Рекомендации на основе истории покупок
    purchased_categories = Order.objects.filter(user=user).values_list(
        'items__product__category', flat=True
    ).distinct()
    
    recommendations = Product.objects.filter(
        category__in=purchased_categories,
        is_active=True,
        is_featured=True
    ).exclude(
        order_items__order__user=user
    ).distinct()[:6]
    
    # Если рекомендаций мало, добавляем популярные товары
    if recommendations.count() < 6:
        popular = Product.objects.filter(
            is_active=True,
            is_featured=True
        ).exclude(id__in=recommendations.values_list('id', flat=True))[:6-recommendations.count()]
        recommendations = list(recommendations) + list(popular)
    
    return recommendations


def get_user_notifications(user):
    """Получение уведомлений пользователя"""
    # Здесь можно добавить модель уведомлений
    # Пока возвращаем пустой список
    return []


def get_bonus_transactions(user):
    """Получение истории операций с бонусами"""
    # Здесь можно добавить модель транзакций бонусов
    # Пока возвращаем пустой список
    return []


def get_bonus_recommendations(user):
    """Получение рекомендаций по использованию бонусов"""
    return [
        {
            'title': 'Получите скидку 10%',
            'description': 'Потратьте 500 бонусов для получения скидки 10%',
            'cost': 500,
            'benefit': '10% скидка'
        },
        {
            'title': 'Бесплатная доставка',
            'description': 'Потратьте 200 бонусов для бесплатной доставки',
            'cost': 200,
            'benefit': 'Бесплатная доставка'
        }
    ]


def get_available_bonus_actions(user):
    """Получение доступных действий с бонусами"""
    return [
        {
            'action': 'discount',
            'title': 'Получить скидку',
            'description': 'Обменять бонусы на скидку'
        },
        {
            'action': 'free_delivery',
            'title': 'Бесплатная доставка',
            'description': 'Обменять бонусы на бесплатную доставку'
        }
    ]


def get_monthly_spending_stats(user):
    """Получение статистики расходов по месяцам"""
    # Здесь можно добавить SQL-запрос для группировки по месяцам
    return []


def get_user_top_categories(user):
    """Получение топ категорий пользователя"""
    # Здесь можно добавить агрегированный запрос
    return []


def get_user_activity_stats(user):
    """Получение статистики активности"""
    return {
        'days_since_registration': (timezone.now().date() - user.date_joined.date()).days,
        'last_order_date': Order.objects.filter(user=user).first().created_at.date() if Order.objects.filter(user=user).exists() else None,
        'average_orders_per_month': 0
    }


def create_user_data_package(user):
    """Создание пакета данных пользователя"""
    # Здесь можно создать архив с данными пользователя
    import io
    import zipfile
    
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zip_file:
        # Добавляем файл с профилем
        profile_data = f"User Profile:\nName: {user.get_full_name()}\nEmail: {user.email}\nPhone: {user.phone}\n"
        zip_file.writestr('profile.txt', profile_data)
    
    buffer.seek(0)
    return buffer.getvalue()


def get_user_support_tickets(user):
    """Получение тикетов поддержки пользователя"""
    # Здесь можно добавить модель тикетов поддержки
    return []


def get_frequently_asked_questions():
    """Получение часто задаваемых вопросов"""
    return [
        {
            'question': 'Как отследить мой заказ?',
            'answer': 'Вы можете отследить заказ в разделе "История заказов" в личном кабинете.'
        },
        {
            'question': 'Как вернуть товар?',
            'answer': 'Для возврата товара обратитесь в службу поддержки через форму обратной связи.'
        }
    ]


def calculate_loyalty_level(user):
    """Расчет уровня лояльности пользователя"""
    total_spent = user.total_spent
    
    if total_spent >= 100000:
        return 'platinum'
    elif total_spent >= 50000:
        return 'gold'
    elif total_spent >= 10000:
        return 'silver'
    else:
        return 'bronze'


def get_loyalty_level_benefits(level):
    """Получение преимуществ уровня лояльности"""
    benefits = {
        'bronze': ['Базовые скидки', 'Участие в акциях'],
        'silver': ['Увеличенные скидки', 'Приоритетная поддержка', 'Эксклюзивные предложения'],
        'gold': ['Максимальные скидки', 'Бесплатная доставка', 'Персональный менеджер'],
        'platinum': ['Все преимущества Gold', 'VIP обслуживание', 'Ранний доступ к новинкам']
    }
    return benefits.get(level, [])


def get_next_level_progress(user):
    """Получение прогресса до следующего уровня"""
    current_level = calculate_loyalty_level(user)
    total_spent = user.total_spent
    
    thresholds = {
        'bronze': 10000,
        'silver': 50000,
        'gold': 100000,
        'platinum': float('inf')
    }
    
    current_threshold = thresholds.get(current_level, 0)
    next_threshold = thresholds.get(next(iter(thresholds.get(current_level, 'bronze')), 'silver'), 10000)
    
    progress = min((total_spent - current_threshold) / (next_threshold - current_threshold), 1)
    
    return {
        'current': current_level,
        'next': next(iter(thresholds.get(current_level, 'silver')), 'silver'),
        'progress': progress,
        'amount_needed': max(next_threshold - total_spent, 0)
    }


def get_available_loyalty_rewards(user):
    """Получение доступных наград программы лояльности"""
    level = calculate_loyalty_level(user)
    
    rewards = {
        'bronze': [
            {'title': 'Скидка 5%', 'cost': 1000, 'description': 'Скидка на следующую покупку'}
        ],
        'silver': [
            {'title': 'Скидка 10%', 'cost': 2000, 'description': 'Увеличенная скидка'},
            {'title': 'Бесплатная доставка', 'cost': 1500, 'description': 'Один заказ с бесплатной доставкой'}
        ],
        'gold': [
            {'title': 'Скидка 15%', 'cost': 3000, 'description': 'Максимальная скидка'},
            {'title': 'Подарок', 'cost': 2500, 'description': 'Подарок от магазина'}
        ],
        'platinum': [
            {'title': 'VIP сервис', 'cost': 5000, 'description': 'Персональное обслуживание'}
        ]
    }
    

# Аутентификация и регистрация

def logout_view(request):
    """
    Выход из системы с кастомным шаблоном
    """
    from django.contrib.auth import logout

    logout(request)
    return render(request, 'accounts/logout.html')


def register(request):
    """
    Регистрация нового пользователя
    """
    from .forms import RegistrationForm
    from django.contrib.auth import login
    from django.core.mail import send_mail
    from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
    from django.contrib.sites.shortcuts import get_current_site
    from django.template.loader import render_to_string
    from django.utils.encoding import force_bytes, force_str
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.is_active = False  # Делаем неактивным до подтверждения email
                    user.save()
                    
                    # Отправляем email для подтверждения
                    send_verification_email(request, user)
                    
                    messages.success(request, 'Регистрация успешна! Проверьте email для подтверждения.')
                    return redirect('accounts:registration_complete')
                    
            except Exception as e:
                messages.error(request, f'Ошибка при регистрации: {str(e)}')
    else:
        form = RegistrationForm()
    
    context = {
        'form': form,
        'title': 'Регистрация'
    }
    
    return render(request, 'accounts/register.html', context)


def registration_complete(request):
    """
    Страница завершения регистрации
    """
    return render(request, 'accounts/registration_complete.html')


def verify_email(request, token):
    """
    Подтверждение email по токену
    """
    from .tokens import email_verification_token
    from django.utils.http import urlsafe_base64_decode
    
    try:
        uid = urlsafe_base64_decode(token.split('_')[0]).decode()
        token = token.split('_')[1]
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and email_verification_token.check_token(user, token):
        user.is_email_verified = True
        user.is_active = True
        user.save()
        messages.success(request, 'Email подтвержден! Аккаунт активирован.')
        return redirect('accounts:login')
    else:
        messages.error(request, 'Недействительная ссылка для подтверждения.')
        return redirect('home')


def email_verification_sent(request):
    """
    Страница отправки email для подтверждения
    """
    return render(request, 'accounts/email_verification_sent.html')


def resend_email_verification(request):
    """
    Повторная отправка email для подтверждения
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            if not user.is_email_verified:
                send_verification_email(request, user)
                messages.success(request, 'Email для подтверждения повторно отправлен.')
            else:
                messages.info(request, 'Email уже подтвержден.')
        except User.DoesNotExist:
            messages.error(request, 'Пользователь с таким email не найден.')
        
        return redirect('accounts:email_verification_sent')
    
    return render(request, 'accounts/resend_verification.html')


def activate_account(request, uidb64, token):
    """
    Активация аккаунта
    """
    from django.utils.http import urlsafe_base64_decode
    from django.contrib.auth.tokens import default_token_generator
    
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Аккаунт успешно активирован!')
        return redirect('accounts:login')
    else:
        messages.error(request, 'Недействительная ссылка для активации.')
        return redirect('home')


def activation_sent(request):
    """
    Страница отправки ссылки активации
    """
    return render(request, 'accounts/activation_sent.html')


@login_required
def profile(request):
    """
    Личный кабинет пользователя
    """
    user = request.user

    # Получаем или создаем профиль
    profile, created = UserProfile.objects.get_or_create(user=user)

    # Получаем статистику пользователя
    stats = get_user_dashboard_stats(user)

    context = {
        'user': user,
        'profile': profile,
        'stats': stats
    }

    return render(request, 'accounts/profile.html', context)


def edit_profile(request):
    """
    Редактирование профиля
    """
    return profile_update(request)


def profile_settings(request):
    """
    Настройки профиля
    """
    return account_settings(request)


def address_list(request):
    """
    Список адресов
    """
    return addresses_list(request)


def add_address(request):
    """
    Добавление адреса
    """
    return address_create(request)


def edit_address(request, address_id):
    """
    Редактирование адреса
    """
    return address_update(request, address_id)


def delete_address(request, address_id):
    """
    Удаление адреса
    """
    return address_delete(request, address_id)


def set_default_address(request, address_id):
    """
    Установка адреса по умолчанию
    """
    return address_set_default(request, address_id)


def preferences(request):
    """
    Настройки предпочтений
    """
    return notification_settings(request)


def communication_preferences(request):
    """
    Настройки связи
    """
    if request.method == 'POST':
        # Обработка настроек связи
        pass
    return render(request, 'accounts/communication_preferences.html')


def privacy_settings(request):
    """
    Настройки приватности
    """
    if request.method == 'POST':
        # Обработка настроек приватности
        pass
    return render(request, 'accounts/privacy_settings.html')


def data_export(request):
    """
    Экспорт данных пользователя
    """
    return download_data(request)


def export_status(request, request_id):
    """
    Статус экспорта данных
    """
    return JsonResponse({'status': 'processing'})


def download_export(request, request_id):
    """
    Скачивание экспорта данных
    """
    return HttpResponse('Export not ready')


def request_data_deletion(request):
    """
    Запрос удаления данных
    """
    if request.method == 'POST':
        # Обработка запроса удаления данных
        pass
    return render(request, 'accounts/request_data_deletion.html')


def confirm_data_deletion(request, request_id):
    """
    Подтверждение удаления данных
    """
    return JsonResponse({'status': 'confirmed'})


def cancel_data_deletion(request, request_id):
    """
    Отмена удаления данных
    """
    return JsonResponse({'status': 'cancelled'})


def age_verification(request):
    """
    Проверка возраста
    """
    return render(request, 'accounts/age_verification.html')


def confirm_age_verification(request):
    """
    Подтверждение проверки возраста
    """
    if request.method == 'POST':
        request.session['age_verified'] = True
        return redirect('home')
    return redirect('accounts:age_verification')


# Дополнительные функции

def send_verification_email(request, user):
    """
    Отправка email для подтверждения
    """
    from .tokens import email_verification_token
    from django.contrib.sites.shortcuts import get_current_site
    
    current_site = get_current_site(request)
    subject = 'Подтвердите ваш email'
    
    # Создаем токен
    token = email_verification_token.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # Создаем ссылку для подтверждения
    verification_link = f"{current_site.domain}/accounts/email-verify/{uid}_{token}/"
    
    # Формируем сообщение
    message = f"""
    Здравствуйте, {user.first_name or user.username}!
    
    Спасибо за регистрацию на нашем сайте.
    
    Для подтверждения вашего email адреса, пожалуйста, перейдите по ссылке:
    {verification_link}
    
    Если вы не регистрировались на нашем сайте, просто проигнорируйте это сообщение.
    
    С уважением,
    Команда PhoneShop
    """
    
    # Отправляем email
    send_mail(subject, message, None, [user.email], fail_silently=True)


def mark_all_notifications_read(request):
    """
    Отметить все уведомления как прочитанные
    """
    if request.user.is_authenticated:
        # Здесь можно добавить логику отметки уведомлений как прочитанных
        pass
    return JsonResponse({'status': 'success'})
    return rewards.get(level, [])


# Дополнительные заглушки для URL маршрутов

def deactivate_account(request):
    """Деактивация аккаунта"""
    if request.method == 'POST':
        user = request.user
        user.is_active = False
        user.save()
        messages.success(request, 'Аккаунт деактивирован')
        return redirect('home')
    return render(request, 'accounts/deactivate_account.html')

def delete_account_confirmation(request):
    """Подтверждение удаления аккаунта"""
    return render(request, 'accounts/delete_account_confirmation.html')

def check_username_availability(request):
    """Проверка доступности имени пользователя"""
    return JsonResponse({'available': True})

def check_email_availability(request):
    """Проверка доступности email"""
    return JsonResponse({'available': True})

def check_phone_availability(request):
    """Проверка доступности телефона"""
    return JsonResponse({'available': True})

def api_register(request):
    """API регистрация"""
    return JsonResponse({'status': 'success'})

def api_login(request):
    """API вход"""
    return JsonResponse({'status': 'success'})

def api_logout(request):
    """API выход"""
    return JsonResponse({'status': 'success'})

def api_profile(request):
    """API профиль"""
    return JsonResponse({'profile': {}})

def api_change_password(request):
    """API смена пароля"""
    return JsonResponse({'status': 'success'})

def api_forgot_password(request):
    """API восстановление пароля"""
    return JsonResponse({'status': 'success'})

def api_reset_password(request, token):
    """API сброс пароля"""
    return JsonResponse({'status': 'success'})

def phone_verification(request):
    """Верификация телефона"""
    return render(request, 'accounts/phone_verification.html')

def send_phone_verification(request):
    """Отправка SMS для верификации"""
    return JsonResponse({'status': 'sent'})

def confirm_phone_verification(request):
    """Подтверждение SMS кода"""
    return JsonResponse({'status': 'verified'})

def security_settings(request):
    """Настройки безопасности"""
    return render(request, 'accounts/security_settings.html')

def active_sessions(request):
    """Активные сессии"""
    return render(request, 'accounts/active_sessions.html')

def terminate_session(request, session_id):
    """Завершение сессии"""
    return JsonResponse({'status': 'terminated'})

def two_factor_setup(request):
    """Настройка двухфакторной аутентификации"""
    return render(request, 'accounts/two_factor_setup.html')

def two_factor_verify(request):
    """Подтверждение двухфакторной аутентификации"""
    return JsonResponse({'status': 'verified'})

def two_factor_disable(request):
    """Отключение двухфакторной аутентификации"""
    return JsonResponse({'status': 'disabled'})

def activity_log(request):
    """Журнал активности"""
    return render(request, 'accounts/activity_log.html')

def activity_log_data(request):
    """Данные журнала активности"""
    return JsonResponse({'activities': []})

def bonus_dashboard(request):
    """Дашборд бонусной программы"""
    return render(request, 'accounts/bonus_dashboard.html')

def bonus_history(request):
    """История бонусов"""
    return render(request, 'accounts/bonus_history.html')

def referral_program(request):
    """Программа рефералов"""
    return render(request, 'accounts/referral_program.html')

def get_referral_code(request):
    """Получение реферального кода"""
    return JsonResponse({'code': 'REF123'})

def partner_program(request):
    """Партнерская программа"""
    return render(request, 'accounts/partner_program.html')

def notifications(request):
    """Уведомления"""
    return render(request, 'accounts/notifications.html')

def mark_notification_read(request, notification_id):
    """Отметка уведомления как прочитанного"""
    return JsonResponse({'status': 'marked'})
