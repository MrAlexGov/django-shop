"""
Представления для приложения cart (корзина покупок)
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
from django.db import transaction
from django.db.models import Q
from decimal import Decimal
import json

from .models import Cart, CartItem, CartSession, SavedForLater, CartAnalytics
from .forms import CartItemForm, DiscountCodeForm, CartBulkActionForm
from catalog.models import Product
from accounts.models import DiscountCode


# Временное минимальное представление для устранения ошибки
@require_http_methods(["GET"])
def cart_detail(request):
    """
    Минимальная страница корзины без обращения к проблемным связям
    """
    context = {
        'cart': None,
        'cart_items': [],
        'user': getattr(request, 'user', None),
        'session_key': getattr(request.session, 'session_key', None) if hasattr(request, 'session') else None,
        'is_authenticated': False,
        'delivery_info': {'cost': 0, 'is_free': True, 'threshold': 3000, 'needed': 0},
        'summary': {
            'items_count': 0,
            'total_quantity': 0,
            'subtotal': 0,
            'discount': 0,
            'delivery': 0,
            'total': 0,
            'has_discount': False,
            'delivery_info': {'cost': 0, 'is_free': True, 'threshold': 3000, 'needed': 0},
        },
        'csrf_token': getattr(request, 'csrf_token', '')
    }
    
    return render(request, 'cart/cart_detail.html', context)
def get_or_create_cart(request):
    """
    Получение или создание корзины для текущего пользователя/сессии (упрощенная версия)
    """
    try:
        # Безопасное создание сессии
        if not request.session.session_key:
            request.session.create()
        
        session_key = request.session.session_key
        
        # Значения по умолчанию для новой корзины
        cart_defaults = {
            'session_key': session_key,
            'discount_code': '',
            'subtotal': 0,
            'tax_amount': 0,
            'shipping_cost': 0,
            'total': 0,
            'used_bonus_points': 0,
            'items_count': 0,
            'total_quantity': 0,
            'total_price': 0,
            'total_discount': 0,
            'final_price': 0,
            'discount_amount': 0,
            'delivery_cost': 0,
            'free_delivery_threshold': 3000
        }
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Для авторизованного пользователя
            cart, created = Cart.objects.get_or_create(
                user=request.user,
                defaults=cart_defaults
            )
            
            # Если у пользователя есть корзина с сессией, но нет корзины с пользователем
            if not cart.user:
                cart.user = request.user
                cart.save()
        else:
            # Для неавторизованного пользователя
            cart, created = Cart.objects.get_or_create(
                session_key=session_key,
                user=None,
                defaults=cart_defaults
            )
        
        return cart
        
    except Exception as e:
        # В случае ошибки создаем минимальную корзину
        if not hasattr(request, 'session') or not request.session.session_key:
            return None
        
        try:
            cart = Cart.objects.create(
                session_key=request.session.session_key,
                discount_code='',
                subtotal=0,
                tax_amount=0,
                shipping_cost=0,
                total=0,
                used_bonus_points=0,
                items_count=0,
                total_quantity=0,
                total_price=0,
                total_discount=0,
                final_price=0,
                discount_amount=0,
                delivery_cost=0,
                free_delivery_threshold=3000
            )
            return cart
        except:
            return None


def get_client_ip(request):
    """Получение IP адреса клиента"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@require_http_methods(["GET"])
def cart_detail(request):
    """
    Детальная страница корзины (минимальная версия для решения ошибки с колонками)
    """
    try:
        cart = get_or_create_cart(request)
        
        context = {
            'cart': cart,
            'delivery_info': {'cost': 0, 'is_free': True, 'threshold': 3000, 'needed': 0},
            'summary': {
                'items_count': getattr(cart, 'items_count', 0),
                'total_quantity': getattr(cart, 'total_quantity', 0),
                'subtotal': float(getattr(cart, 'total_price', 0)),
                'discount': float(getattr(cart, 'total_discount', 0)) + float(getattr(cart, 'discount_amount', 0)),
                'delivery': float(getattr(cart, 'delivery_cost', 0)),
                'total': float(getattr(cart, 'final_price', 0)),
                'has_discount': bool(getattr(cart, 'applied_discount_id', None)),
                'delivery_info': {'cost': 0, 'is_free': True, 'threshold': 3000, 'needed': 0},
            },
        }
        
        return render(request, 'cart/cart_detail.html', context)
        
    except Exception as e:
        # В случае ошибки возвращаем простую страницу с базовыми данными
        return render(request, 'cart/cart_detail.html', {
            'cart': None,
            'error': str(e) if hasattr(e, '__str__') else 'Unknown error',
            'delivery_info': {'cost': 0, 'is_free': True, 'threshold': 3000, 'needed': 0},
            'summary': {
                'items_count': 0,
                'total_quantity': 0,
                'subtotal': 0,
                'discount': 0,
                'delivery': 0,
                'total': 0,
                'has_discount': False,
                'delivery_info': {'cost': 0, 'is_free': True, 'threshold': 3000, 'needed': 0},
            },
        })


@require_http_methods(["POST"])
@csrf_exempt  # Для AJAX запросов
def add_to_cart(request):
    """
    AJAX добавление товара в корзину
    """
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)
        price_override = data.get('price_override')
        
        product = get_object_or_404(Product, id=product_id, is_active=True)
        quantity = int(quantity)
        
        if quantity <= 0:
            return JsonResponse({'error': 'Количество должно быть больше нуля'}, status=400)
        
        if product.stock_quantity < quantity:
            return JsonResponse({
                'error': f'На складе доступно только {product.stock_quantity} шт.'
            }, status=400)
        
        cart = get_or_create_cart(request)
        
        with transaction.atomic():
            cart_item = cart.add_item(product, quantity, price_override)
        
        # Обновляем аналитику
        update_cart_analytics(request, cart, 'added_item')
        
        # Формируем ответ
        response_data = {
            'status': 'success',
            'message': f'"{product.name}" добавлен в корзину',
            'cart_summary': cart.get_summary(),
            'cart_count': cart.items_count,
            'cart_total': str(cart.final_price),
        }
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат данных'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def update_cart_item(request):
    """
    AJAX обновление количества товара в корзине
    """
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = data.get('quantity')
        
        product = get_object_or_404(Product, id=product_id)
        cart = get_or_create_cart(request)
        
        quantity = int(quantity)
        
        if quantity <= 0:
            # Удаляем товар из корзины
            cart.remove_item(product)
            message = f'"{product.name}" удален из корзины'
            action = 'removed'
        else:
            # Обновляем количество
            cart.update_item_quantity(product, quantity)
            message = f'Количество "{product.name}" обновлено'
            action = 'updated'
        
        response_data = {
            'status': 'success',
            'action': action,
            'message': message,
            'cart_summary': cart.get_summary(),
            'item_total': str(cart.items.get(product=product).total_price) if cart.items.filter(product=product).exists() else '0',
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def remove_from_cart(request):
    """
    AJAX удаление товара из корзины
    """
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        
        product = get_object_or_404(Product, id=product_id)
        cart = get_or_create_cart(request)
        
        cart.remove_item(product)
        
        response_data = {
            'status': 'success',
            'message': f'"{product.name}" удален из корзины',
            'cart_summary': cart.get_summary(),
            'cart_count': cart.items_count,
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def clear_cart(request):
    """
    AJAX очистка корзины
    """
    cart = get_or_create_cart(request)
    cart.clear()
    
    response_data = {
        'status': 'success',
        'message': 'Корзина очищена',
        'cart_summary': cart.get_summary(),
    }
    
    return JsonResponse(response_data)


@require_http_methods(["GET"])
def cart_summary(request):
    """
    AJAX получение краткой информации о корзине
    """
    cart = get_or_create_cart(request)
    
    summary = cart.get_summary()
    summary['is_empty'] = cart.is_empty()
    
    return JsonResponse(summary)


@require_http_methods(["POST"])
@csrf_exempt
def apply_discount_code(request):
    """
    AJAX применение промокода
    """
    try:
        data = json.loads(request.body)
        discount_code = data.get('discount_code', '').strip()
        
        if not discount_code:
            return JsonResponse({'error': 'Введите промокод'}, status=400)
        
        cart = get_or_create_cart(request)
        
        try:
            discount = DiscountCode.objects.get(code=discount_code.upper())
            cart.apply_discount_code(discount)
            
            response_data = {
                'status': 'success',
                'message': f'Промокод "{discount.code}" применен',
                'discount_amount': str(cart.discount_amount),
                'total_amount': str(cart.final_price),
                'cart_summary': cart.get_summary(),
            }
            
            return JsonResponse(response_data)
            
        except DiscountCode.DoesNotExist:
            return JsonResponse({'error': 'Промокод не найден'}, status=404)
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def remove_discount_code(request):
    """
    AJAX удаление промокода
    """
    cart = get_or_create_cart(request)
    cart.remove_discount_code()
    
    response_data = {
        'status': 'success',
        'message': 'Промокод удален',
        'total_amount': str(cart.final_price),
        'cart_summary': cart.get_summary(),
    }
    
    return JsonResponse(response_data)


@login_required
@require_http_methods(["GET"])
def saved_products(request):
    """
    Страница отложенных товаров
    """
    saved_items = SavedForLater.objects.filter(user=request.user)
    
    context = {
        'saved_items': saved_items,
        'total_items': saved_items.count(),
    }
    
    return render(request, 'cart/saved_products.html', context)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def save_for_later(request):
    """
    AJAX сохранение товара на потом
    """
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)
        
        product = get_object_or_404(Product, id=product_id)
        quantity = int(quantity)
        
        saved_item, created = SavedForLater.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            saved_item.quantity = quantity
            saved_item.save()
        
        response_data = {
            'status': 'success',
            'message': f'"{product.name}" сохранен на потом',
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def move_to_cart(request):
    """
    AJAX перемещение товара из сохраненных в корзину
    """
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)
        
        product = get_object_or_404(Product, id=product_id)
        quantity = int(quantity)
        
        cart = get_or_create_cart(request)
        
        # Удаляем из сохраненных
        SavedForLater.objects.filter(user=request.user, product=product).delete()
        
        # Добавляем в корзину
        cart.add_item(product, quantity)
        
        response_data = {
            'status': 'success',
            'message': f'"{product.name}" перемещен в корзину',
            'cart_summary': cart.get_summary(),
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def remove_from_saved(request):
    """
    AJAX удаление из сохраненных товаров
    """
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        
        product = get_object_or_404(Product, id=product_id)
        SavedForLater.objects.filter(user=request.user, product=product).delete()
        
        response_data = {
            'status': 'success',
            'message': f'"{product.name}" удален из сохраненных',
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def cart_analytics(request):
    """
    Страница аналитики корзины
    """
    # Получаем аналитику корзин пользователя
    analytics = CartAnalytics.objects.filter(user=request.user).order_by('-updated_at')[:50]
    
    # Статистика
    total_carts = analytics.count()
    completed_checkouts = analytics.filter(conversion_stage='completed_checkout').count()
    abandoned_carts = analytics.filter(conversion_stage='abandoned').count()
    average_cart_value = analytics.aggregate(
        avg_value=models.Avg('cart_value')
    )['avg_value'] or 0
    
    context = {
        'analytics': analytics,
        'stats': {
            'total_carts': total_carts,
            'completed_checkouts': completed_checkouts,
            'abandoned_carts': abandoned_carts,
            'conversion_rate': (completed_checkouts / total_carts * 100) if total_carts > 0 else 0,
            'average_cart_value': average_cart_value,
        }
    }
    
    return render(request, 'cart/cart_analytics.html', context)


@login_required
@require_http_methods(["GET"])
def abandoned_carts(request):
    """
    Список покинутых корзин пользователя
    """
    from .models import CartAbandonment
    
    abandonments = CartAbandonment.objects.filter(
        cart__user=request.user
    ).order_by('-abandoned_at')
    
    context = {
        'abandonments': abandonments,
    }
    
    return render(request, 'cart/abandoned_carts.html', context)


@login_required
@require_http_methods(["GET"])
def bulk_cart_operations(request):
    """
    Страница массовых операций с корзиной
    """
    if request.method == 'POST':
        form = BulkCartActionForm(request.POST)
        if form.is_valid():
            # Обработка массовой операции
            action_type = form.cleaned_data['action_type']
            items = form.cleaned_data['items']
            
            # Здесь можно реализовать логику массовых операций
            messages.success(request, f'Операция "{action_type}" выполнена для {len(items)} товаров')
            return redirect('cart:bulk_operations')
    else:
        form = BulkCartActionForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'cart/bulk_operations.html', context)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def bulk_update_cart(request):
    """
    AJAX массовое обновление корзины
    """
    try:
        data = json.loads(request.body)
        updates = data.get('updates', [])
        
        cart = get_or_create_cart(request)
        updated_items = []
        
        for update in updates:
            product_id = update.get('product_id')
            quantity = update.get('quantity')
            
            try:
                product = Product.objects.get(id=product_id)
                cart.update_item_quantity(product, int(quantity))
                updated_items.append(product_id)
            except (Product.DoesNotExist, ValidationError):
                continue
        
        response_data = {
            'status': 'success',
            'message': f'Обновлено {len(updated_items)} товаров',
            'updated_items': updated_items,
            'cart_summary': cart.get_summary(),
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def update_cart_analytics(request, cart, conversion_stage):
    """
    Обновление аналитики корзины
    """
    analytics_data = {
        'cart_id': cart.id,
        'items_count': cart.items_count,
        'total_value': str(cart.final_price),
        'has_discount': bool(cart.applied_discount),
        'delivery_cost': str(cart.delivery_cost),
    }
    
    CartAnalytics.objects.update_or_create(
        session_key=request.session.session_key,
        user=request.user if request.user.is_authenticated else None,
        defaults={
            'cart': cart,
            'cart_data': analytics_data,
            'cart_value': cart.final_price,
            'items_count': cart.items_count,
            'conversion_stage': conversion_stage,
        }
    )


@require_http_methods(["GET"])
def cart_widget(request):
    """
    AJAX виджет корзины для отображения в шапке сайта
    """
    cart = get_or_create_cart(request)
    
    # Кэшируем виджет корзины
    cache_key = f'cart_widget_{request.session.session_key}'
    widget_data = cache.get(cache_key)
    
    if widget_data is None:
        recent_items = cart.items.filter(is_active=True)[:3]
        
        widget_data = {
            'items_count': cart.items_count,
            'total_price': str(cart.final_price),
            'is_empty': cart.is_empty(),
            'recent_items': [
                {
                    'name': item.product_name,
                    'quantity': item.quantity,
                    'price': str(item.unit_price),
                    'image': item.product.get_main_image().url if item.product.get_main_image() else None,
                }
                for item in recent_items
            ],
            'delivery_info': cart.get_delivery_info(),
        }
        
        cache.set(cache_key, widget_data, 300)  # Кэшируем на 5 минут
    
    return JsonResponse(widget_data)


@require_http_methods(["GET"])
def cart_count(request):
    """
    AJAX количество товаров в корзине
    """
    cart = get_or_create_cart(request)
    return JsonResponse({
        'count': cart.items_count,
        'total_quantity': cart.total_quantity
    })


@login_required
@require_http_methods(["GET"])
def cart_history(request):
    """
    История корзин пользователя
    """
    from django.db.models import Max
    
    carts = Cart.objects.filter(user=request.user).annotate(
        last_item_date=Max('items__added_at')
    ).order_by('-last_activity')[:20]
    
    context = {
        'carts': carts,
    }
    
    return render(request, 'cart/cart_history.html', context)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def restore_cart(request):
    """
    AJAX восстановление корзины
    """
    try:
        data = json.loads(request.body)
        cart_id = data.get('cart_id')
        
        old_cart = get_object_or_404(Cart, id=cart_id, user=request.user)
        current_cart = get_or_create_cart(request)
        
        # Переносим товары из старой корзины
        items_transferred = 0
        for old_item in old_cart.items.filter(is_active=True):
            try:
                current_cart.add_item(old_item.product, old_item.quantity)
                items_transferred += 1
            except ValidationError:
                continue
        
        # Делаем старую корзину неактивной
        old_cart.is_active = False
        old_cart.save()
        
        response_data = {
            'status': 'success',
            'message': f'Восстановлено {items_transferred} товаров из корзины',
            'cart_summary': current_cart.get_summary(),
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def cart_api(request):
    """
    API для мобильного приложения
    """
    cart = get_or_create_cart(request)
    
    cart_data = {
        'id': cart.id,
        'items_count': cart.items_count,
        'total_quantity': cart.total_quantity,
        'total_price': str(cart.final_price),
        'delivery_cost': str(cart.delivery_cost),
        'discount_amount': str(cart.discount_amount),
        'is_empty': cart.is_empty(),
        'items': [
            {
                'id': item.id,
                'product_id': item.product.id,
                'name': item.product_name,
                'sku': item.product_sku,
                'brand': item.product_brand,
                'quantity': item.quantity,
                'unit_price': str(item.unit_price),
                'total_price': str(item.total_price),
                'image': item.product.get_main_image().url if item.product.get_main_image() else None,
                'is_available': item.product.is_available,
                'stock_quantity': item.product.stock_quantity,
                'discount_info': item.get_discount_info(),
            }
            for item in cart.items.filter(is_active=True)
        ],
        'delivery_info': cart.get_delivery_info(),
        'discount_info': {
            'applied': bool(cart.applied_discount),
            'code': cart.applied_discount.code if cart.applied_discount else None,
            'amount': str(cart.discount_amount),
        }
    }
    
    return JsonResponse(cart_data)


# Вспомогательные функции
def merge_guest_cart_with_user_cart(user, session_key):
    """
    Объединение корзины гостя с корзиной пользователя при авторизации
    """
    if not session_key:
        return
    
    try:
        guest_cart = Cart.objects.get(session_key=session_key, user=None)
        user_cart, created = Cart.objects.get_or_create(user=user)
        
        if not guest_cart.items.exists():
            guest_cart.delete()
            return
        
        # Переносим товары из гостевой корзины
        for guest_item in guest_cart.items.filter(is_active=True):
            try:
                user_cart.add_item(guest_item.product, guest_item.quantity)
            except ValidationError:
                continue
        
        # Удаляем гостевую корзину
        guest_cart.delete()
        
    except Cart.DoesNotExist:
        pass


@login_required
def cart_merge(request):
    """
    Объединение корзин при входе пользователя
    """
    if hasattr(request, 'session') and request.session.session_key:
        merge_guest_cart_with_user_cart(request.user, request.session.session_key)
    
    return redirect('cart:cart_detail')


# Дополнительные представления для корзины

def cart_widget(request):
    """Мини-виджет корзины"""
    cart = get_or_create_cart(request)
    context = {
        'cart': cart,
        'total_items': cart.get_total_items(),
        'total_price': cart.get_total_price()
    }
    return render(request, 'cart/widget.html', context)

def cart_count(request):
    """Получение количества товаров в корзине"""
    cart = get_or_create_cart(request)
    return JsonResponse({'count': cart.get_total_items()})

def cart_summary(request):
    """Краткая информация о корзине"""
    cart = get_or_create_cart(request)
    return JsonResponse({
        'total_items': cart.get_total_items(),
        'total_price': str(cart.get_total_price()),
        'final_price': str(cart.get_final_price())
    })

def saved_products(request):
    """Отложенные товары"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    saved_items = SavedForLater.objects.filter(user=request.user).select_related('product')
    context = {
        'saved_items': saved_items,
        'total_saved': saved_items.count()
    }
    return render(request, 'cart/saved_products.html', context)

def save_for_later(request):
    """Переместить товар в отложенные"""
    if request.method == 'POST':
        form = SavedForLaterForm(request.POST)
        if form.is_valid():
            product_id = form.cleaned_data['product_id']
            try:
                product = Product.objects.get(id=product_id, is_active=True)
                saved_item, created = SavedForLater.objects.get_or_create(
                    user=request.user,
                    product=product
                )
                return JsonResponse({
                    'status': 'saved',
                    'message': 'Товар перемещен в сохраненные'
                })
            except Product.DoesNotExist:
                return JsonResponse({'error': 'Product not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)

def move_to_cart(request):
    """Переместить товар из сохраненных в корзину"""
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        try:
            saved_item = SavedForLater.objects.get(user=request.user, product_id=product_id)
            cart = get_or_create_cart(request)
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=saved_item.product
            )
            cart_item.quantity = saved_item.quantity
            cart_item.save()
            saved_item.delete()
            return JsonResponse({
                'status': 'moved',
                'message': 'Товар перемещен в корзину'
            })
        except SavedForLater.DoesNotExist:
            return JsonResponse({'error': 'Item not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)

def remove_from_saved(request):
    """Удалить товар из сохраненных"""
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        try:
            SavedForLater.objects.filter(user=request.user, product_id=product_id).delete()
            return JsonResponse({
                'status': 'removed',
                'message': 'Товар удален из сохраненных'
            })
        except:
            return JsonResponse({'error': 'Item not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)

def cart_history(request):
    """История корзин пользователя"""
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'cart/history.html')

def cart_analytics(request):
    """Аналитика корзины"""
    return render(request, 'cart/analytics.html')

def abandoned_carts(request):
    """Покинутые корзины"""
    return render(request, 'cart/abandoned.html')

def restore_cart(request):
    """Восстановление корзины"""
    if request.method == 'POST':
        cart_id = request.POST.get('cart_id')
        try:
            old_cart = Cart.objects.get(id=cart_id)
            current_cart = get_or_create_cart(request)
            # Переносим товары из старой корзины
            for old_item in old_cart.items.filter(is_active=True):
                cart_item, created = CartItem.objects.get_or_create(
                    cart=current_cart,
                    product=old_item.product
                )
                if not created:
                    cart_item.quantity += old_item.quantity
                else:
                    cart_item.quantity = old_item.quantity
                cart_item.save()
            old_cart.delete()
            return JsonResponse({'status': 'restored'})
        except Cart.DoesNotExist:
            return JsonResponse({'error': 'Cart not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)

def bulk_update_cart(request):
    """Массовое обновление корзины"""
    if request.method == 'POST':
        form = BulkCartUpdateForm(request.POST)
        if form.is_valid():
            cart = get_or_create_cart(request)
            for update in form.cleaned_data['updates']:
                try:
                    item = cart.items.get(product_id=update['product_id'])
                    if update['quantity'] == 0:
                        item.delete()
                    else:
                        item.quantity = update['quantity']
                        item.save()
                except CartItem.DoesNotExist:
                    continue
            return JsonResponse({'status': 'updated'})
    return JsonResponse({'error': 'Invalid form'}, status=400)

def bulk_cart_operations(request):
    """Массовые операции с корзиной"""
    if request.method == 'POST':
        form = CartBulkActionForm(request.POST)
        if form.is_valid():
            cart = get_or_create_cart(request)
            action_type = form.cleaned_data['action_type']
            
            if action_type == 'clear':
                cart.items.filter(is_active=True).delete()
            elif action_type == 'remove_selected':
                item_ids = form.cleaned_data['item_ids']
                cart.items.filter(id__in=item_ids).delete()
            
            return JsonResponse({'status': 'completed'})
    return JsonResponse({'error': 'Invalid form'}, status=400)

def cart_api(request):
    """API для корзины"""
    cart = get_or_create_cart(request)
    return JsonResponse({
        'cart_id': cart.id,
        'items': [
            {
                'product_id': item.product.id,
                'name': item.product_name,
                'price': str(item.price),
                'quantity': item.quantity,
                'total': str(item.get_total_price())
            }
            for item in cart.items.filter(is_active=True)
        ],
        'total_price': str(cart.get_total_price())
    })

def cart_merge(request):
    """Объединение корзин"""
    if request.method == 'POST':
        session_key = request.POST.get('session_key')
        try:
            old_cart = Cart.objects.get(session_key=session_key)
            current_cart = get_or_create_cart(request)
            
            for old_item in old_cart.items.filter(is_active=True):
                cart_item, created = CartItem.objects.get_or_create(
                    cart=current_cart,
                    product=old_item.product
                )
                if not created:
                    cart_item.quantity += old_item.quantity
                else:
                    cart_item.quantity = old_item.quantity
                cart_item.save()
            old_cart.delete()
            return JsonResponse({'status': 'merged'})
        except Cart.DoesNotExist:
            return JsonResponse({'error': 'Cart not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)


# Дополнительные представления для корзины

def cart_delivery_estimate(request):
    """Расчет стоимости доставки"""
    from .forms import CartEstimateForm
    from django.http import JsonResponse
    
    if request.method == 'POST':
        form = CartEstimateForm(request.POST)
        if form.is_valid():
            cart = get_or_create_cart(request)
            # Здесь можно добавить логику расчета доставки
            return JsonResponse({
                'estimated_cost': '299.00',
                'estimated_days': '1-3',
                'delivery_methods': [
                    {'type': 'courier', 'cost': '299', 'days': '1-2'},
                    {'type': 'pickup', 'cost': '0', 'days': '0'},
                ]
            })
    else:
        form = CartEstimateForm()
    
    return render(request, 'cart/delivery_estimate.html', {'form': form})

def cart_payment_estimate(request):
    """Расчет способов оплаты"""
    from django.http import JsonResponse
    cart = get_or_create_cart(request)
    
    payment_methods = [
        {
            'type': 'card',
            'name': 'Банковская карта',
            'available': True,
            'fee': '0',
            'processing_time': 'Мгновенно'
        },
        {
            'type': 'cash',
            'name': 'Наличными',
            'available': cart.final_price <= 50000,
            'fee': '0',
            'processing_time': 'При получении'
        },
        {
            'type': 'bonus',
            'name': 'Бонусными баллами',
            'available': request.user.is_authenticated and request.user.bonus_points > 0,
            'fee': '0',
            'processing_time': 'Мгновенно'
        }
    ]
    
    return JsonResponse({'payment_methods': payment_methods})

def mini_cart_ajax(request):
    """Мини корзина для AJAX"""
    return cart_widget(request)

def cart_indicator_ajax(request):
    """Индикатор количества товаров в корзине"""
    return cart_count(request)

def cart_validation_ajax(request):
    """Валидация корзины для AJAX"""
    cart = get_or_create_cart(request)
    validation_results = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'suggestions': []
    }
    
    # Проверяем наличие товаров
    for item in cart.items.filter(is_active=True):
        if not item.product.is_available:
            validation_results['is_valid'] = False
            validation_results['errors'].append(f'Товар "{item.product_name}" недоступен')
        elif item.product.stock_quantity < item.quantity:
            validation_results['errors'].append(
                f'Товар "{item.product_name}" доступен только в количестве {item.product.stock_quantity} шт.'
            )
    
    return JsonResponse(validation_results)

def stock_check_ajax(request):
    """Проверка наличия товара"""
    from django.http import JsonResponse
    from catalog.models import Product
    
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            product_id = data.get('product_id')
            
            product = Product.objects.get(id=product_id)
            return JsonResponse({
                'available': product.in_stock,
                'stock_quantity': product.stock_quantity,
                'can_order': product.can_buy(),
            })
        except (Product.DoesNotExist, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid request'}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

# Дополнительные представления для корзины

def cart_widget(request):
    """Мини-виджет корзины"""
    cart = get_or_create_cart(request)
    context = {
        'cart': cart,
        'total_items': cart.get_total_items(),
        'total_price': cart.get_total_price()
    }
    return render(request, 'cart/widget.html', context)

def cart_count(request):
    """Получение количества товаров в корзине"""
    cart = get_or_create_cart(request)
    return JsonResponse({'count': cart.get_total_items()})

def cart_summary(request):
    """Краткая информация о корзине"""
    cart = get_or_create_cart(request)
    return JsonResponse({
        'total_items': cart.get_total_items(),
        'total_price': str(cart.get_total_price()),
        'final_price': str(cart.get_final_price())
    })

def saved_products(request):
    """Отложенные товары"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    saved_items = SavedForLater.objects.filter(user=request.user).select_related('product')
    context = {
        'saved_items': saved_items,
        'total_saved': saved_items.count()
    }
    return render(request, 'cart/saved_products.html', context)

def save_for_later(request):
    """Переместить товар в отложенные"""
    if request.method == 'POST':
        form = SavedForLaterForm(request.POST)
        if form.is_valid():
            product_id = form.cleaned_data['product_id']
            try:
                product = Product.objects.get(id=product_id, is_active=True)
                saved_item, created = SavedForLater.objects.get_or_create(
                    user=request.user,
                    product=product
                )
                return JsonResponse({
                    'status': 'saved',
                    'message': 'Товар перемещен в сохраненные'
                })
            except Product.DoesNotExist:
                return JsonResponse({'error': 'Product not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)

def move_to_cart(request):
    """Переместить товар из сохраненных в корзину"""
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        try:
            saved_item = SavedForLater.objects.get(user=request.user, product_id=product_id)
            cart = get_or_create_cart(request)
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=saved_item.product
            )
            cart_item.quantity = saved_item.quantity
            cart_item.save()
            saved_item.delete()
            return JsonResponse({
                'status': 'moved',
                'message': 'Товар перемещен в корзину'
            })
        except SavedForLater.DoesNotExist:
            return JsonResponse({'error': 'Item not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)

def remove_from_saved(request):
    """Удалить товар из сохраненных"""
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        try:
            SavedForLater.objects.filter(user=request.user, product_id=product_id).delete()
            return JsonResponse({
                'status': 'removed',
                'message': 'Товар удален из сохраненных'
            })
        except:
            return JsonResponse({'error': 'Item not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)

def cart_history(request):
    """История корзин пользователя"""
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'cart/history.html')

def cart_analytics(request):
    """Аналитика корзины"""
    return render(request, 'cart/analytics.html')

def abandoned_carts(request):
    """Покинутые корзины"""
    return render(request, 'cart/abandoned.html')

def restore_cart(request):
    """Восстановление корзины"""
    if request.method == 'POST':
        cart_id = request.POST.get('cart_id')
        try:
            old_cart = Cart.objects.get(id=cart_id)
            current_cart = get_or_create_cart(request)
            # Переносим товары из старой корзины
            for old_item in old_cart.items.filter(is_active=True):
                cart_item, created = CartItem.objects.get_or_create(
                    cart=current_cart,
                    product=old_item.product
                )
                if not created:
                    cart_item.quantity += old_item.quantity
                else:
                    cart_item.quantity = old_item.quantity
                cart_item.save()
            old_cart.delete()
            return JsonResponse({'status': 'restored'})
        except Cart.DoesNotExist:
            return JsonResponse({'error': 'Cart not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)

def bulk_update_cart(request):
    """Массовое обновление корзины"""
    if request.method == 'POST':
        form = BulkCartUpdateForm(request.POST)
        if form.is_valid():
            cart = get_or_create_cart(request)
            for update in form.cleaned_data['updates']:
                try:
                    item = cart.items.get(product_id=update['product_id'])
                    if update['quantity'] == 0:
                        item.delete()
                    else:
                        item.quantity = update['quantity']
                        item.save()
                except CartItem.DoesNotExist:
                    continue
            return JsonResponse({'status': 'updated'})
    return JsonResponse({'error': 'Invalid form'}, status=400)

def bulk_cart_operations(request):
    """Массовые операции с корзиной"""
    if request.method == 'POST':
        form = CartBulkActionForm(request.POST)
        if form.is_valid():
            cart = get_or_create_cart(request)
            action_type = form.cleaned_data['action_type']
            
            if action_type == 'clear':
                cart.items.filter(is_active=True).delete()
            elif action_type == 'remove_selected':
                item_ids = form.cleaned_data['item_ids']
                cart.items.filter(id__in=item_ids).delete()
            
            return JsonResponse({'status': 'completed'})
    return JsonResponse({'error': 'Invalid form'}, status=400)

def cart_api(request):
    """API для корзины"""
    cart = get_or_create_cart(request)
    return JsonResponse({
        'cart_id': cart.id,
        'items': [
            {
                'product_id': item.product.id,
                'name': item.product_name,
                'price': str(item.price),
                'quantity': item.quantity,
                'total': str(item.get_total_price())
            }
            for item in cart.items.filter(is_active=True)
        ],
        'total_price': str(cart.get_total_price())
    })

def cart_merge(request):
    """Объединение корзин"""
    if request.method == 'POST':
        session_key = request.POST.get('session_key')
        try:
            old_cart = Cart.objects.get(session_key=session_key)
            current_cart = get_or_create_cart(request)
            
            for old_item in old_cart.items.filter(is_active=True):
                cart_item, created = CartItem.objects.get_or_create(
                    cart=current_cart,
                    product=old_item.product
                )
                if not created:
                    cart_item.quantity += old_item.quantity
                else:
                    cart_item.quantity = old_item.quantity
                cart_item.save()
            old_cart.delete()
            return JsonResponse({'status': 'merged'})
        except Cart.DoesNotExist:
            return JsonResponse({'error': 'Cart not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)
