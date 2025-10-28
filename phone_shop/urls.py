"""
Основные URL маршруты проекта PhoneShop
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Главная страница
    path('', include('core.urls')),
    
    # Аутентификация
    path('accounts/', include('accounts.urls')),
    
    # Каталог товаров
    path('catalog/', include('catalog.urls')),
    
    # Корзина покупок
    path('cart/', include('cart.urls')),
    
    # Заказы
    path('orders/', include('orders.urls')),
    
    # Блог
    path('blog/', include('blog.urls')),
    
    # Перенаправление на каталог
    path('shop/', RedirectView.as_view(pattern_name='catalog:product_list', permanent=False)),
]

# Обслуживание медиафайлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS)
