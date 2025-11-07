"""
URL маршруты для приложения cart (корзина покупок)
"""

from django.urls import path
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from . import views

app_name = 'cart'

urlpatterns = [
    # Основные страницы корзины
    path('', views.cart_detail, name='cart_detail'),
    
    # AJAX эндпоинты для управления корзиной
    path('add/', views.add_to_cart_api, name='add_to_cart'),
    path('update/', views.update_item_quantity_api, name='update_item_quantity'),
    path('remove/', views.remove_item_api, name='remove_item'),
    path('clear/', views.clear_cart_api, name='clear_cart'),
    
    # Промокоды
    path('apply-promo-code/', views.apply_promo_code_api, name='apply_promo_code'),
    path('remove-promo-code/', views.remove_promo_code_api, name='remove_promo_code'),
    
    # Дополнительные AJAX эндпоинты
    path('ajax/mini-cart/', views.mini_cart_ajax, name='mini_cart'),
    path('ajax/cart-indicator/', views.cart_indicator_ajax, name='cart_indicator_ajax'),
    path('ajax/get-cart-count/', views.get_cart_count, name='get_cart_count'),
    
    # Валидация и проверка
    path('ajax/add-multiple/', views.add_multiple_items_api, name='add_multiple_items'),
    path('ajax/validate/', views.cart_validation_ajax, name='cart_validation'),
    path('ajax/stock-check/', views.stock_check_ajax, name='stock_check'),
]