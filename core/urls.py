"""
URLs для основного приложения core
"""

from django.urls import path
from .views import (
    HomeView, contact, about, delivery, payment,
    returns, privacy, terms, sitemap, shop
)

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('about/', about, name='about'),
    path('contact/', contact, name='contact'),
    path('delivery/', delivery, name='delivery'),
    path('payment/', payment, name='payment'),
    path('returns/', returns, name='returns'),
    path('privacy/', privacy, name='privacy'),
    path('terms/', terms, name='terms'),
    path('sitemap/', sitemap, name='sitemap'),
    path('shop/', shop, name='shop'),
]