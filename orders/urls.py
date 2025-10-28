"""
URL маршруты для приложения orders (заказы)
"""

from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from . import views

app_name = 'orders'

urlpatterns = [
    # Основные страницы
    path('', login_required(views.order_list), name='order_list'),
    path('create/', login_required(views.create_order), name='create_order'),
    path('success/<str:order_number>/', login_required(views.order_success), name='order_success'),
    path('detail/<str:order_number>/', login_required(views.order_detail), name='order_detail'),
    
    # Оформление заказа в 3 шага
    path('checkout/step1/', login_required(views.checkout_step1), name='checkout_step1'),
    path('checkout/step2/', login_required(views.checkout_step2), name='checkout_step2'),
    path('checkout/step3/', login_required(views.checkout_step3), name='checkout_step3'),
    
    # Операции с заказами
    path('cancel/<str:order_number>/', login_required(views.cancel_order), name='cancel_order'),
    path('return/<str:order_number>/', login_required(views.request_return), name='request_return'),
    path('tracking/<str:order_number>/', login_required(views.order_tracking), name='order_tracking'),
    
    # API для мобильного приложения
    path('api/', login_required(views.order_api), name='order_api'),
    path('api/status/<str:order_number>/', login_required(views.order_status_api), name='order_status_api'),
    
    # Документы и информация
    path('receipt/<str:order_number>/', login_required(views.order_receipt), name='order_receipt'),
]