"""
Представления для приложения orders (заказы)
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
from django.db.models import Q
from django.utils import timezone
from decimal import Decimal
import json

from .models import Order, OrderItem, OrderHistory, Payment, Shipment, OrderReturn
from cart.models import Cart
from accounts.models import Address, User
from catalog.models import Product
from .forms import CheckoutStep1Form, CheckoutStep2Form, CheckoutStep3Form, OrderSearchForm


def get_or_create_cart(request):
    """Получение корзины пользователя"""
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


@login_required
@require_http_methods(["GET", "POST"])
def checkout_step1(request):
    """
    Шаг 1 оформления заказа: Данные о доставке
    Корзина → данные (адрес доставки, способ доставки)
    """
    cart = get_or_create_cart(request)
    
    # Проверяем, есть ли товары в корзине
    if cart.is_empty():
        messages.warning(request, 'Ваша корзина пуста')
        return redirect('cart:cart_detail')
    
    if request.method == 'POST':
        form = CheckoutStep1Form(request.POST, user=request.user)
        if form.is_valid():
            # Сохраняем данные первого шага в сессии
            request.session['checkout_step1'] = form.cleaned_data
            return redirect('orders:checkout_step2')
    else:
        # Предзаполняем форму данными из сессии или профиля
        initial_data = request.session.get('checkout_step1', {})
        if not initial_data and request.user.profile.addresses.exists():
            default_address = request.user.profile.addresses.filter(is_default=True).first()
            if default_address:
                initial_data = {
                    'address_id': default_address.id,
                    'delivery_method': 'courier',
                    'delivery_date': timezone.now().date(),
                    'delivery_time_slot': '',
                    'delivery_comment': ''
                }
        form = CheckoutStep1Form(initial=initial_data, user=request.user)
    
    context = {
        'cart': cart,
        'form': form,
        'summary': cart.get_summary(),
        'step': 1,
        'total_steps': 3
    }
    
    return render(request, 'orders/checkout_step1.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def checkout_step2(request):
    """
    Шаг 2 оформления заказа: Способ оплаты
    """
    # Проверяем, что первый шаг завершен
    if 'checkout_step1' not in request.session:
        messages.warning(request, 'Сначала заполните данные о доставке')
        return redirect('orders:checkout_step1')
    
    cart = get_or_create_cart(request)
    
    if request.method == 'POST':
        form = CheckoutStep2Form(request.POST, user=request.user, bonus_balance=request.user.bonus_points)
        if form.is_valid():
            # Сохраняем данные второго шага в сессии
            request.session['checkout_step2'] = form.cleaned_data
            return redirect('orders:checkout_step3')
    else:
        # Предзаполняем форму данными из сессии
        initial_data = request.session.get('checkout_step2', {})
        form = CheckoutStep2Form(initial=initial_data, user=request.user, bonus_balance=request.user.bonus_points)
    
    context = {
        'cart': cart,
        'form': form,
        'summary': cart.get_summary(),
        'step': 2,
        'total_steps': 3,
        'step1_data': request.session.get('checkout_step1', {})
    }
    
    return render(request, 'orders/checkout_step2.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def checkout_step3(request):
    """
    Шаг 3 оформления заказа: Подтверждение
    """
    # Проверяем, что первые два шага завершены
    if 'checkout_step1' not in request.session or 'checkout_step2' not in request.session:
        messages.warning(request, 'Сначала заполните все данные')
        return redirect('orders:checkout_step1')
    
    cart = get_or_create_cart(request)
    step1_data = request.session.get('checkout_step1', {})
    step2_data = request.session.get('checkout_step2', {})
    
    if request.method == 'POST':
        form = CheckoutStep3Form(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Создаем заказ
                    order = create_order_from_cart(request, cart, step1_data, step2_data)
                    
                    # Очищаем сессию checkout
                    del request.session['checkout_step1']
                    del request.session['checkout_step2']
                    
                    messages.success(request, f'Заказ #{order.order_number} успешно создан!')
                    return redirect('orders:order_success', order_number=order.order_number)
                    
            except Exception as e:
                messages.error(request, f'Ошибка при создании заказа: {str(e)}')
                return redirect('orders:checkout_step3')
    else:
        form = CheckoutStep3Form()
    
    # Дополнительная информация для подтверждения
    delivery_address = get_object_or_404(Address, id=step1_data.get('address_id'))
    payment_method = step2_data.get('payment_method', 'card')
    
    context = {
        'cart': cart,
        'form': form,
        'summary': cart.get_summary(),
        'step': 3,
        'total_steps': 3,
        'step1_data': step1_data,
        'step2_data': step2_data,
        'delivery_address': delivery_address,
        'payment_method': payment_method,
        'user': request.user
    }
    
    return render(request, 'orders/checkout_step3.html', context)


def create_order_from_cart(request, cart, step1_data, step2_data):
    """Создание заказа из корзины"""
    user = request.user
    delivery_address = get_object_or_404(Address, id=step1_data.get('address_id'))
    
    # Создаем заказ
    order = Order.objects.create(
        user=user,
        billing_address=delivery_address,
        shipping_address=delivery_address,
        delivery_method=step1_data.get('delivery_method'),
        delivery_date=step1_data.get('delivery_date'),
        delivery_time_slot=step1_data.get('delivery_time_slot'),
        delivery_comment=step1_data.get('delivery_comment', ''),
        payment_method=step2_data.get('payment_method'),
        customer_note=step2_data.get('customer_note', ''),
        gift_message=step2_data.get('gift_message', ''),
        gift_wrapping=step2_data.get('gift_wrapping', False),
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        source='web'
    )
    
    # Копируем товары из корзины в заказ
    for cart_item in cart.items.filter(is_active=True):
        OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            quantity=cart_item.quantity,
            unit_price=cart_item.unit_price,
            product_name=cart_item.product_name,
            product_sku=cart_item.product_sku,
            product_brand=cart_item.product_brand,
            warranty_months=cart_item.product.warranty_months
        )
    
    # Копируем данные о скидках
    if cart.applied_discount:
        order.applied_discount = cart.applied_discount
        if cart.applied_discount.is_valid():
            cart.applied_discount.use_code()
    
    order.bonus_points_used = step2_data.get('bonus_points_to_use', 0)
    
    # Списываем бонусные баллы
    if order.bonus_points_used > 0:
        user.spend_bonus_points(order.bonus_points_used)
    
    # Рассчитываем итоговые суммы
    order.save()
    
    # Очищаем корзину
    cart.clear()
    
    # Создаем историю заказа
    OrderHistory.objects.create(
        order=order,
        user=user,
        action='Заказ создан',
        comment='Заказ создан через веб-интерфейс'
    )
    
    return order


@login_required
@require_http_methods(["GET"])
def order_success(request, order_number):
    """
    Страница успешного создания заказа
    """
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    context = {
        'order': order,
        'estimated_delivery': calculate_estimated_delivery(order)
    }
    
    return render(request, 'orders/order_success.html', context)


@login_required
@require_http_methods(["GET"])
def order_detail(request, order_number):
    """
    Детальная страница заказа
    """
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    context = {
        'order': order,
        'shipment': order.shipments.first(),
        'payments': order.payments.all(),
        'returns': order.returns.all() if request.user.is_staff else None,
        'can_cancel': order.can_cancel(),
        'can_return': order.can_return(),
        'estimated_delivery': calculate_estimated_delivery(order)
    }
    
    return render(request, 'orders/order_detail.html', context)


@login_required
@require_http_methods(["GET"])
def order_list(request):
    """
    Список заказов пользователя
    """
    orders = Order.objects.filter(user=request.user).select_related().prefetch_related('items')
    
    # Фильтрация
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Поиск
    search_query = request.GET.get('q')
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(items__product_name__icontains=search_query)
        )
    
    # Пагинация
    from django.core.paginator import Paginator
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'orders': page_obj.object_list,
        'status_choices': Order.STATUS_CHOICES,
        'current_status': status_filter,
        'search_query': search_query
    }
    
    return render(request, 'orders/order_list.html', context)


@login_required
@require_http_methods(["POST"])
def cancel_order(request, order_number):
    """
    Отмена заказа
    """
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    if not order.can_cancel():
        messages.error(request, 'Заказ нельзя отменить')
        return redirect('orders:order_detail', order_number=order_number)
    
    try:
        with transaction.atomic():
            order.update_status('cancelled', user=request.user)
            
            # Возвращаем бонусные баллы
            if order.bonus_points_used > 0:
                order.user.add_bonus_points(order.bonus_points_used)
            
            # Возвращаем товары на склад
            for item in order.items.filter(is_active=True):
                item.product.stock_quantity += item.quantity
                item.product.save(update_fields=['stock_quantity'])
            
            messages.success(request, 'Заказ успешно отменен')
            
    except Exception as e:
        messages.error(request, f'Ошибка при отмене заказа: {str(e)}')
    
    return redirect('orders:order_detail', order_number=order_number)


@login_required
@require_http_methods(["POST"])
def request_return(request, order_number):
    """
    Запрос на возврат товара
    """
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    if not order.can_return():
        messages.error(request, 'Возврат недоступен для данного заказа')
        return redirect('orders:order_detail', order_number=order_number)
    
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        reason = data.get('reason')
        reason_text = data.get('reason_text', '')
        
        order_item = get_object_or_404(OrderItem, id=item_id, order=order)
        
        return_request = OrderReturn.objects.create(
            order=order,
            order_item=order_item,
            reason=reason,
            reason_text=reason_text,
            quantity=order_item.quantity,
            refund_amount=order_item.total_price
        )
        
        messages.success(request, 'Запрос на возврат отправлен')
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def order_tracking(request, order_number):
    """
    Отслеживание доставки заказа
    """
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    shipment = order.shipments.first()
    
    if not shipment or not shipment.tracking_number:
        messages.warning(request, 'Отслеживание недоступно')
        return redirect('orders:order_detail', order_number=order_number)
    
    # Здесь можно интегрироваться с API служб доставки
    tracking_info = get_tracking_info(shipment)
    
    context = {
        'order': order,
        'shipment': shipment,
        'tracking_info': tracking_info
    }
    
    return render(request, 'orders/order_tracking.html', context)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def check_stock_availability(request):
    """
    AJAX проверка наличия товаров для заказа
    """
    try:
        data = json.loads(request.body)
        items = data.get('items', [])
        
        unavailable_items = []
        for item_data in items:
            product_id = item_data.get('product_id')
            quantity = item_data.get('quantity', 1)
            
            try:
                product = Product.objects.get(id=product_id, is_active=True)
                if product.stock_quantity < quantity:
                    unavailable_items.append({
                        'product_id': product_id,
                        'product_name': product.name,
                        'requested': quantity,
                        'available': product.stock_quantity
                    })
            except Product.DoesNotExist:
                unavailable_items.append({
                    'product_id': product_id,
                    'error': 'Товар не найден'
                })
        
        return JsonResponse({
            'status': 'success',
            'unavailable_items': unavailable_items,
            'all_available': len(unavailable_items) == 0
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def order_analytics(request):
    """
    Аналитика заказов пользователя
    """
    user_orders = Order.objects.filter(user=request.user)
    
    # Общая статистика
    total_orders = user_orders.count()
    total_spent = user_orders.aggregate(
        total=models.Sum('total_amount')
    )['total'] or Decimal('0.00')
    
    # Статистика по статусам
    status_stats = user_orders.values('status').annotate(
        count=models.Count('id')
    ).order_by('status')
    
    # Статистика по месяцам (последние 12 месяцев)
    from django.utils import timezone
    twelve_months_ago = timezone.now().date() - timezone.timedelta(days=365)
    monthly_stats = user_orders.filter(
        created_at__gte=twelve_months_ago
    ).extra(
        select={'month': 'strftime("%%Y-%%m", created_at)'}
    ).values('month').annotate(
        count=models.Count('id'),
        total=models.Sum('total_amount')
    ).order_by('month')
    
    context = {
        'total_orders': total_orders,
        'total_spent': total_spent,
        'status_stats': status_stats,
        'monthly_stats': monthly_stats,
        'average_order_value': total_spent / total_orders if total_orders > 0 else 0
    }
    
    return render(request, 'orders/order_analytics.html', context)


@login_required
@require_http_methods(["GET"])
def order_search(request):
    """
    Поиск заказов
    """
    form = OrderSearchForm(request.GET)
    orders = Order.objects.filter(user=request.user)
    
    if form.is_valid():
        order_number = form.cleaned_data.get('order_number')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        status = form.cleaned_data.get('status')
        min_amount = form.cleaned_data.get('min_amount')
        max_amount = form.cleaned_data.get('max_amount')
        
        if order_number:
            orders = orders.filter(order_number__icontains=order_number)
        if date_from:
            orders = orders.filter(created_at__date__gte=date_from)
        if date_to:
            orders = orders.filter(created_at__date__lte=date_to)
        if status:
            orders = orders.filter(status=status)
        if min_amount:
            orders = orders.filter(total_amount__gte=min_amount)
        if max_amount:
            orders = orders.filter(total_amount__lte=max_amount)
    
    # Пагинация
    from django.core.paginator import Paginator
    paginator = Paginator(orders.select_related().prefetch_related('items'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'orders': page_obj.object_list,
        'results_count': orders.count()
    }
    
    return render(request, 'orders/order_search.html', context)


@login_required
@require_http_methods(["GET"])
def order_export(request):
    """
    Экспорт заказов в CSV/Excel
    """
    import csv
    from django.http import HttpResponse
    
    orders = Order.objects.filter(user=request.user)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="orders_{timezone.now().date()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Номер заказа', 'Дата', 'Статус', 'Сумма', 'Способ оплаты', 
        'Способ доставки', 'Количество товаров'
    ])
    
    for order in orders:
        writer.writerow([
            order.order_number,
            order.created_at.strftime('%Y-%m-%d %H:%M'),
            order.get_status_display(),
            order.total_amount,
            order.get_payment_method_display(),
            order.get_delivery_method_display(),
            order.items.count()
        ])
    
    return response


# Вспомогательные функции

def calculate_estimated_delivery(order):
    """Расчет предполагаемой даты доставки"""
    from datetime import timedelta
    
    base_days = {
        'courier': 3,
        'pickup': 1,
        'express': 1,
        'post': 7
    }
    
    delivery_days = base_days.get(order.delivery_method, 3)
    
    if order.delivery_method == 'express':
        return timezone.now().date() + timedelta(days=1)
    else:
        return order.delivery_date or (timezone.now().date() + timedelta(days=delivery_days))


def get_tracking_info(shipment):
    """Получение информации об отслеживании (заглушка)"""
    # Здесь должна быть интеграция с API служб доставки
    return {
        'status': 'В пути',
        'current_location': 'Москва',
        'estimated_delivery': shipment.estimated_delivery,
        'events': [
            {'date': '2025-01-15', 'location': 'Москва', 'status': 'Отправлен'},
            {'date': '2025-01-16', 'location': 'Москва', 'status': 'В обработке'},
        ]
    }


@login_required
@require_http_methods(["GET"])
def order_api(request):
    """
    API для мобильного приложения - список заказов
    """
    orders = Order.objects.filter(user=request.user).select_related().prefetch_related('items')
    
    orders_data = []
    for order in orders:
        orders_data.append({
            'id': order.id,
            'order_number': order.order_number,
            'status': order.status,
            'status_display': order.get_status_display(),
            'total_amount': str(order.total_amount),
            'created_at': order.created_at.isoformat(),
            'items_count': order.items.count(),
            'estimated_delivery': calculate_estimated_delivery(order).isoformat() if calculate_estimated_delivery(order) else None,
        })
    
    return JsonResponse({
        'orders': orders_data,
        'pagination': {
            'total': orders.count(),
            'page': request.GET.get('page', 1),
            'per_page': 20
        }
    })


@login_required
@require_http_methods(["GET"])
def order_status_api(request, order_number):
    """
    API для получения статуса заказа
    """
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    return JsonResponse({
        'order_number': order.order_number,
        'status': order.status,
        'status_display': order.get_status_display(),
        'created_at': order.created_at.isoformat(),
        'updated_at': order.updated_at.isoformat(),
        'estimated_delivery': calculate_estimated_delivery(order).isoformat() if calculate_estimated_delivery(order) else None,
        'can_cancel': order.can_cancel(),
        'can_return': order.can_return()
    })


# Уведомления и интеграция

@login_required
@require_http_methods(["POST"])
def send_order_notification(request, order_number):
    """
    Отправка уведомления о заказе
    """
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # Здесь можно добавить логику отправки уведомлений
    messages.success(request, 'Уведомление отправлено')
    return redirect('orders:order_detail', order_number=order_number)


@login_required
@require_http_methods(["GET"])
def order_receipt(request, order_number):
    """
    Получение чека заказа
    """
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    context = {
        'order': order,
        'receipt_number': f"R-{order.order_number}"
    }
    
    return render(request, 'orders/receipt.html', context)


@login_required
@require_http_methods(["GET"])
def order_warranty(request, order_number):
    """
    Гарантийные обязательства
    """
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    context = {
        'order': order,
        'warranty_info': get_warranty_info(order)
    }
    
    return render(request, 'orders/warranty.html', context)


def get_warranty_info(order):
    """Информация о гарантии"""
    return {
        'default_warranty': '12 месяцев',
        'official_warranty': True,
        'service_centers': [
            {'name': 'Сервисный центр Apple', 'address': 'Москва, ул. Тверская, 1'},
            {'name': 'Сервисный центр Samsung', 'address': 'Москва, ул. Арбат, 15'},
        ],
        'warranty_conditions': [
            'Гарантия действует в течение 12 месяцев с даты покупки',
            'Гарантия не распространяется на механические повреждения',
            'Требуется сохранение гарантийного талона и чека',
        ]
    }

def create_order(request):
    """Создание заказа (прямое создание, минуя корзину)"""
    return redirect('orders:checkout_step1')
