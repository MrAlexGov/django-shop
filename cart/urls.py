"""
URL маршруты для приложения cart (корзина покупок)
"""

from django.urls import path, include
from django.views.generic import TemplateView
from django.http import JsonResponse
from . import views

app_name = 'cart'

urlpatterns = [
    # Основные страницы корзины (временно упрощено для решения проблемы с БД)
    path('', views.cart_detail, name='cart_detail'),
    # AJAX эндпоинты для JavaScript
    path('add/', views.add_to_cart_api, name='add_to_cart'),
    path('update/', views.update_item_quantity_api, name='update_item_quantity'),
    path('remove/', views.remove_item_api, name='remove_item'),
    path('clear/', views.clear_cart_api, name='clear_cart'),
    
    # Промокоды
    path('apply-promo-code/', views.apply_promo_code_api, name='apply_promo_code'),
    path('remove-promo-code/', views.remove_promo_code_api, name='remove_promo_code'),
    
    # Дополнительные AJAX эндпоинты (временные заглушки)
    path('ajax/mini-cart/', lambda request: JsonResponse({'items_count': 0, 'total_price': 0, 'items': []}), name='mini_cart'),
    path('ajax/cart-indicator/', lambda request: JsonResponse({'count': 0, 'total': 0}), name='cart_indicator_ajax'),
    path('ajax/get-cart-count/', lambda request: JsonResponse({'count': 0}), name='get_cart_count'),
    
    # Скидки и промокоды (временно отключено)
    # path('discount/apply/', views.apply_discount_code, name='apply_discount'),  
    # path('discount/remove/', views.remove_discount_code, name='remove_discount'),  
    
    # Сохраненные товары (временно отключено)
    # path('saved/', views.saved_products, name='saved_products'),  # Временно отключено
    # path('save-for-later/', views.save_for_later, name='save_for_later'),  # Временно отключено
    # path('move-to-cart/', views.move_to_cart, name='move_to_cart'),  # Временно отключено
    # path('remove-from-saved/', views.remove_from_saved, name='remove_from_saved'),  # Временно отключено
    
    # Вспомогательные страницы (временно отключено)
    # path('delivery-estimate/', views.cart_delivery_estimate, name='delivery_estimate'),  
    # path('payment-estimate/', views.cart_payment_estimate, name='payment_estimate'),  
    
    # AJAX эндпоинты (временно отключено)
    # path('ajax/mini-cart/', views.mini_cart_ajax, name='mini_cart_ajax'),  
    # path('ajax/cart-indicator/', views.cart_indicator_ajax, name='cart_indicator_ajax'),  
    # path('ajax/cart-validation/', views.cart_validation_ajax, name='cart_validation_ajax'),  
    # path('ajax/stock-check/', views.stock_check_ajax, name='stock_check_ajax'),  
    
    # Простой API (временно отключено)
    # path('api/', views.cart_api, name='cart_api'),
]