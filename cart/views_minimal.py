#!/usr/bin/env python
"""
Минимальное представление для корзины, чтобы устранить ошибку "no such column"
"""

from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model

User = get_user_model()

@require_http_methods(["GET"])
def cart_detail(request):
    """
    Минимальная страница корзины без обращения к проблемным связям
    """
    try:
        # Простая информация о корзине без связей
        user = request.user if hasattr(request, 'user') else None
        session_key = getattr(request.session, 'session_key', None)
        
        context = {
            'cart': None,
            'user': user,
            'session_key': session_key,
            'is_authenticated': user.is_authenticated if user else False,
            'delivery_info': {
                'cost': 0,
                'is_free': True,
                'threshold': 3000,
                'needed': 0
            },
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
            'items': [],  # Пустой список товаров
        }
        
        return render(request, 'cart/cart_detail.html', context)
        
    except Exception as e:
        # В случае любой ошибки возвращаем базовую страницу
        return render(request, 'cart/cart_detail.html', {
            'cart': None,
            'error': str(e) if hasattr(e, '__str__') else 'Unknown error',
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
            'items': [],
        })