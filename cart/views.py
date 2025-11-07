"""
Представления для приложения cart (корзина покупок)
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.contrib.auth import get_user_model
from decimal import Decimal
import json

from .models import Cart, CartItem
from catalog.models import Product
from accounts.models import DiscountCode

User = get_user_model()


def get_or_create_cart(request):
    """Получение корзины пользователя или создание новой"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            defaults={'session_key': request.session.session_key}
        )
        if not cart.user:
            cart.user = request.user
            cart.save()
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        
        cart, created = Cart.objects.get_or_create(
            session_key=session_key,
            user=None
        )
    
    return cart


@require_http_methods(["GET"])
def cart_detail(request):
    """
    Страница корзины
    """
    try:
        cart = get_or_create_cart(request)
        
        # Пересчитываем итоговые суммы
        if cart.items.exists():
            cart.calculate_totals()
        
        context = {
            'cart': cart,
            'cart_items': cart.items.filter(is_active=True) if cart else [],
            'csrf_token': request.META.get('CSRF_COOKIE', ''),
            'summary': cart.get_summary() if cart else {
                'items_count': 0,
                'total_quantity': 0,
                'subtotal': 0,
                'discount': 0,
                'delivery': 0,
                'total': 0,
                'has_discount': False,
                'delivery_info': {
                    'cost': 0,
                    'is_free': True,
                    'threshold': 3000,
                    'needed': 0
                }
            },
        }
        
        return render(request, 'cart/cart_detail.html', context)
        
    except Exception as e:
        # В случае ошибки возвращаем базовую страницу
        messages.error(request, f'Ошибка загрузки корзины: {str(e)}')
        return render(request, 'cart/cart_detail.html', {
            'cart': None,
            'cart_items': [],
            'csrf_token': '',
            'summary': {
                'items_count': 0,
                'total_quantity': 0,
                'subtotal': 0,
                'discount': 0,
                'delivery': 0,
                'total': 0,
                'has_discount': False,
                'delivery_info': {
                    'cost': 0,
                    'is_free': True,
                    'threshold': 3000,
                    'needed': 0
                }
            },
        })


@require_http_methods(["POST"])
@csrf_exempt
def add_to_cart_api(request):
    """
    AJAX: Добавление товара в корзину
    """
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        price_override = data.get('price_override')
        
        # Получаем товар
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        # Получаем корзину
        cart = get_or_create_cart(request)
        
        # Добавляем товар
        cart_item = cart.add_item(product, quantity, price_override)
        
        return JsonResponse({
            'success': True,
            'message': f'Товар "{product.name}" добавлен в корзину',
            'cart_summary': cart.get_summary()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@require_http_methods(["POST"])
def update_item_quantity_api(request):
    """
    AJAX: Обновление количества товара
    """
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        new_quantity = int(data.get('quantity'))
        
        # Получаем товар корзины
        cart_item = get_object_or_404(CartItem, id=item_id)
        
        # Проверяем права доступа
        cart = cart_item.cart
        if not has_cart_access(request, cart):
            return JsonResponse({
                'success': False,
                'message': 'У вас нет доступа к этой корзине'
            }, status=403)
        
        # Обновляем количество
        if new_quantity <= 0:
            cart_item.delete()
            message = 'Товар удален из корзины'
        else:
            cart_item.update_quantity(new_quantity)
            message = 'Количество обновлено'
        
        # Пересчитываем итоговые суммы
        cart.calculate_totals()
        
        return JsonResponse({
            'success': True,
            'message': message,
            'cart_summary': cart.get_summary()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@require_http_methods(["POST"])
def remove_item_api(request):
    """
    AJAX: Удаление товара из корзины
    """
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        
        # Получаем товар корзины
        cart_item = get_object_or_404(CartItem, id=item_id)
        
        # Проверяем права доступа
        cart = cart_item.cart
        if not has_cart_access(request, cart):
            return JsonResponse({
                'success': False,
                'message': 'У вас нет доступа к этой корзине'
            }, status=403)
        
        # Удаляем товар
        product_name = cart_item.product_name
        cart_item.delete()
        
        # Пересчитываем итоговые суммы
        cart.calculate_totals()
        
        return JsonResponse({
            'success': True,
            'message': f'Товар "{product_name}" удален из корзины',
            'cart_summary': cart.get_summary()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@require_http_methods(["POST"])
def clear_cart_api(request):
    """
    AJAX: Очистка корзины
    """
    try:
        # Получаем корзину
        cart = get_or_create_cart(request)
        
        # Проверяем права доступа
        if not has_cart_access(request, cart):
            return JsonResponse({
                'success': False,
                'message': 'У вас нет доступа к этой корзине'
            }, status=403)
        
        # Очищаем корзину
        cart.clear()
        
        return JsonResponse({
            'success': True,
            'message': 'Корзина очищена',
            'cart_summary': cart.get_summary()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@require_http_methods(["POST"])
def apply_promo_code_api(request):
    """
    AJAX: Применение промокода
    """
    try:
        data = json.loads(request.body)
        code = data.get('code', '').strip().upper()
        
        if not code:
            return JsonResponse({
                'success': False,
                'message': 'Введите промокод'
            }, status=400)
        
        # Получаем корзину
        cart = get_or_create_cart(request)
        
        # Проверяем права доступа
        if not has_cart_access(request, cart):
            return JsonResponse({
                'success': False,
                'message': 'У вас нет доступа к этой корзине'
            }, status=403)
        
        # Ищем промокод
        try:
            discount = DiscountCode.objects.get(code=code)
            cart.apply_discount_code(discount)
            
            return JsonResponse({
                'success': True,
                'message': f'Промокод "{code}" применен',
                'cart_summary': cart.get_summary()
            })
            
        except DiscountCode.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Промокод не найден'
            }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@require_http_methods(["POST"])
def remove_promo_code_api(request):
    """
    AJAX: Удаление промокода
    """
    try:
        # Получаем корзину
        cart = get_or_create_cart(request)
        
        # Проверяем права доступа
        if not has_cart_access(request, cart):
            return JsonResponse({
                'success': False,
                'message': 'У вас нет доступа к этой корзине'
            }, status=403)
        
        # Удаляем промокод
        cart.remove_discount_code()
        
        return JsonResponse({
            'success': True,
            'message': 'Промокод удален',
            'cart_summary': cart.get_summary()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


def has_cart_access(request, cart):
    """
    Проверка доступа к корзине
    """
    if request.user.is_authenticated:
        return cart.user == request.user
    else:
        session_key = request.session.session_key
        return cart.session_key == session_key


# API эндпоинты для мини-корзины

@require_http_methods(["GET"])
def mini_cart_ajax(request):
    """
    AJAX: Мини-корзина для хедера
    """
    try:
        cart = get_or_create_cart(request)
        items = cart.items.filter(is_active=True)[:5]  # Первые 5 товаров
        
        items_data = []
        for item in items:
            items_data.append({
                'id': item.id,
                'name': item.product_name,
                'quantity': item.quantity,
                'unit_price': str(item.unit_price),
                'total_price': str(item.total_price),
                'image_url': item.product.get_main_image.url if item.product.get_main_image else '',
                'product_url': reverse('catalog:product_detail', kwargs={'slug': item.product.slug})
            })
        
        return JsonResponse({
            'items_count': cart.items_count,
            'total_price': str(cart.final_price),
            'items': items_data,
            'cart_url': reverse('cart:cart_detail')
        })
        
    except Exception as e:
        return JsonResponse({
            'items_count': 0,
            'total_price': '0.00',
            'items': []
        })


@require_http_methods(["GET"])
def cart_indicator_ajax(request):
    """
    AJAX: Индикатор корзины для навигации
    """
    try:
        cart = get_or_create_cart(request)
        
        return JsonResponse({
            'count': cart.items_count,
            'total': str(cart.final_price),
            'is_empty': cart.is_empty()
        })
        
    except Exception as e:
        return JsonResponse({
            'count': 0,
            'total': '0.00',
            'is_empty': True
        })


@require_http_methods(["GET"])
def get_cart_count(request):
    """
    AJAX: Получение количества товаров в корзине
    """
    try:
        cart = get_or_create_cart(request)
        
        return JsonResponse({
            'count': cart.items_count
        })
        
    except Exception as e:
        return JsonResponse({
            'count': 0
        })


# Дополнительные функции

@require_http_methods(["POST"])
def add_multiple_items_api(request):
    """
    AJAX: Добавление нескольких товаров одновременно
    """
    try:
        data = json.loads(request.body)
        items = data.get('items', [])
        
        cart = get_or_create_cart(request)
        results = []
        
        for item_data in items:
            try:
                product_id = item_data.get('product_id')
                quantity = item_data.get('quantity', 1)
                price_override = item_data.get('price_override')
                
                product = Product.objects.get(id=product_id, is_active=True)
                cart_item = cart.add_item(product, quantity, price_override)
                
                results.append({
                    'product_id': product_id,
                    'success': True,
                    'message': f'Товар "{product.name}" добавлен'
                })
                
            except Exception as e:
                results.append({
                    'product_id': item_data.get('product_id'),
                    'success': False,
                    'message': str(e)
                })
        
        # Пересчитываем итоговые суммы
        cart.calculate_totals()
        
        return JsonResponse({
            'success': True,
            'results': results,
            'cart_summary': cart.get_summary()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@require_http_methods(["GET"])
def cart_validation_ajax(request):
    """
    AJAX: Валидация корзины
    """
    try:
        cart = get_or_create_cart(request)
        issues = []
        
        for item in cart.items.filter(is_active=True):
            # Проверяем наличие товара
            if not item.product.is_active:
                issues.append({
                    'type': 'product_inactive',
                    'item_id': item.id,
                    'message': f'Товар "{item.product_name}" больше не доступен'
                })
            
            # Проверяем количество на складе
            if item.quantity > item.product.stock_quantity:
                issues.append({
                    'type': 'insufficient_stock',
                    'item_id': item.id,
                    'message': f'Товар "{item.product_name}" недоступен в заказанном количестве',
                    'available': item.product.stock_quantity
                })
            
            # Проверяем актуальность цены
            if item.unit_price != item.product.price:
                issues.append({
                    'type': 'price_changed',
                    'item_id': item.id,
                    'message': f'Изменилась цена товара "{item.product_name}"',
                    'old_price': str(item.unit_price),
                    'new_price': str(item.product.price)
                })
        
        return JsonResponse({
            'valid': len(issues) == 0,
            'issues': issues
        })
        
    except Exception as e:
        return JsonResponse({
            'valid': False,
            'issues': [{'type': 'error', 'message': str(e)}]
        }, status=500)


@require_http_methods(["GET"])
def stock_check_ajax(request):
    """
    AJAX: Проверка наличия товаров
    """
    try:
        cart = get_or_create_cart(request)
        stock_info = []
        
        for item in cart.items.filter(is_active=True):
            stock_info.append({
                'item_id': item.id,
                'product_id': item.product.id,
                'product_name': item.product_name,
                'requested_quantity': item.quantity,
                'available_quantity': item.product.stock_quantity,
                'in_stock': item.product.stock_quantity >= item.quantity,
                'price': str(item.product.price),
                'old_price': str(item.product.old_price) if item.product.old_price else None
            })
        
        return JsonResponse({
            'items': stock_info,
            'all_in_stock': all(item['in_stock'] for item in stock_info)
        })
        
    except Exception as e:
        return JsonResponse({
            'items': [],
            'all_in_stock': False,
            'error': str(e)
        }, status=500)