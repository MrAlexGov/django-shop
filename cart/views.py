"""
Исправленные представления для корзины покупок
Реализован полный функционал корзины согласно ТЗ
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.urls import reverse
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth import get_user_model
import json
from decimal import Decimal

from .models import Cart, CartItem, CartSession
from catalog.models import Product
from accounts.models import DiscountCode

User = get_user_model()


def get_or_create_cart(request):
    """
    Получить или создать корзину для текущего пользователя/сессии
    """
    if request.user.is_authenticated:
        # Для авторизованных пользователей
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            is_active=True,
            defaults={'session_key': request.session.session_key}
        )
    else:
        # Для неавторизованных пользователей по сессии
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        
        cart, created = Cart.objects.get_or_create(
            session_key=session_key,
            is_active=True
        )
        
        # Обновляем сессию
        if created:
            CartSession.objects.create(
                session_key=session_key,
                cart=cart,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
    
    return cart


def get_client_ip(request):
    """Получить IP адрес клиента"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@require_http_methods(["GET"])
def cart_detail(request):
    """
    Страница корзины покупок
    """
    cart = get_or_create_cart(request)
    cart_items = cart.items.filter(is_active=True).select_related('product')
    
    # Подсчет итогов
    cart.calculate_totals()
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'user': getattr(request, 'user', None),
        'session_key': getattr(request.session, 'session_key', None),
        'is_authenticated': request.user.is_authenticated,
        'delivery_info': cart.get_delivery_info(),
        'summary': cart.get_summary(),
        'csrf_token': getattr(request, 'csrf_token', ''),
    }
    
    return render(request, 'cart/cart_detail.html', context)


@require_http_methods(["POST"])
@csrf_exempt
def add_to_cart(request):
    """
    Добавление товара в корзину
    """
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        
        if quantity <= 0:
            return JsonResponse({
                'success': False,
                'message': 'Количество должно быть больше нуля'
            }, status=400)
        
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        cart = get_or_create_cart(request)
        
        # Проверяем наличие товара
        if product.stock_quantity < quantity:
            return JsonResponse({
                'success': False,
                'message': f'Недостаточно товара на складе. Доступно: {product.stock_quantity} шт.'
            }, status=400)
        
        # Добавляем товар в корзину
        cart_item = cart.add_item(product, quantity)
        
        return JsonResponse({
            'success': True,
            'message': f'Товар "{product.name}" добавлен в корзину',
            'cart_count': cart.items_count,
            'cart_total': str(cart.final_price),
            'cart_summary': cart.get_summary()
        })
        
    except (Product.DoesNotExist, ValueError, json.JSONDecodeError) as e:
        return JsonResponse({
            'success': False,
            'message': 'Ошибка при добавлении товара в корзину'
        }, status=400)


@require_http_methods(["POST"])
@csrf_exempt
def update_item_quantity(request):
    """
    Обновление количества товара в корзине
    """
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        
        product = get_object_or_404(Product, id=product_id)
        cart = get_or_create_cart(request)
        
        if quantity <= 0:
            # Удаляем товар из корзины
            success = cart.remove_item(product)
            if success:
                return JsonResponse({
                    'success': True,
                    'message': 'Товар удален из корзины',
                    'cart_summary': cart.get_summary()
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Товар не найден в корзине'
                }, status=404)
        else:
            # Обновляем количество
            success = cart.update_item_quantity(product, quantity)
            if success:
                cart.calculate_totals()
                return JsonResponse({
                    'success': True,
                    'message': 'Количество обновлено',
                    'cart_summary': cart.get_summary()
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Товар не найден в корзине'
                }, status=404)
                
    except (Product.DoesNotExist, ValueError, json.JSONDecodeError) as e:
        return JsonResponse({
            'success': False,
            'message': 'Ошибка при обновлении количества'
        }, status=400)


@require_http_methods(["POST"])
@csrf_exempt
def remove_item(request):
    """
    Удаление товара из корзины
    """
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        
        product = get_object_or_404(Product, id=product_id)
        cart = get_or_create_cart(request)
        
        success = cart.remove_item(product)
        
        if success:
            cart.calculate_totals()
            return JsonResponse({
                'success': True,
                'message': 'Товар удален из корзины',
                'cart_summary': cart.get_summary()
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Товар не найден в корзине'
            }, status=404)
            
    except (Product.DoesNotExist, json.JSONDecodeError) as e:
        return JsonResponse({
            'success': False,
            'message': 'Ошибка при удалении товара'
        }, status=400)


@require_http_methods(["POST"])
@csrf_exempt
def clear_cart(request):
    """
    Очистка корзины
    """
    cart = get_or_create_cart(request)
    cart.clear()
    
    return JsonResponse({
        'success': True,
        'message': 'Корзина очищена',
        'cart_summary': cart.get_summary()
    })


@require_http_methods(["GET"])
def cart_summary_api(request):
    """
    API для получения краткой информации о корзине
    """
    cart = get_or_create_cart(request)
    
    return JsonResponse({
        'items_count': cart.items_count,
        'total_quantity': cart.total_quantity,
        'total_price': str(cart.final_price),
        'has_items': not cart.is_empty(),
        'delivery_info': cart.get_delivery_info(),
        'summary': cart.get_summary()
    })


@require_http_methods(["POST"])
@csrf_exempt
def apply_discount_code(request):
    """
    Применение промокода
    """
    try:
        data = json.loads(request.body)
        discount_code = data.get('discount_code', '').strip()
        
        if not discount_code:
            return JsonResponse({
                'success': False,
                'message': 'Введите код скидки'
            }, status=400)
        
        # Ищем промокод
        try:
            discount = DiscountCode.objects.get(code=discount_code.upper())
        except DiscountCode.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Недействительный код скидки'
            }, status=404)
        
        cart = get_or_create_cart(request)
        
        # Проверяем минимальную сумму
        if discount.min_order_amount and cart.total_price < discount.min_order_amount:
            return JsonResponse({
                'success': False,
                'message': f'Минимальная сумма для этого промокода: {discount.min_order_amount} ₽'
            }, status=400)
        
        # Применяем промокод
        cart.apply_discount_code(discount)
        
        return JsonResponse({
            'success': True,
            'message': f'Промокод применен! Скидка: {discount.description}',
            'discount_amount': str(cart.discount_amount),
            'cart_summary': cart.get_summary()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Неверный формат запроса'
        }, status=400)


@require_http_methods(["POST"])
@csrf_exempt
def remove_discount_code(request):
    """
    Удаление промокода
    """
    cart = get_or_create_cart(request)
    cart.remove_discount_code()
    
    return JsonResponse({
        'success': True,
        'message': 'Промокод удален',
        'cart_summary': cart.get_summary()
    })


# Миграция старых представлений для совместимости
cart_detail_view = cart_detail
cart_summary = cart_summary_api
add_to_cart_api = add_to_cart
update_item_quantity_api = update_item_quantity
remove_item_api = remove_item
clear_cart_api = clear_cart
apply_promo_code_api = apply_discount_code
remove_promo_code_api = remove_discount_code