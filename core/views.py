from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from django.db.models import Count, Avg, Sum
from django.utils import timezone
from catalog.models import Product, Category, Brand
from blog.models import Article
from cart.models import Cart

class HomeView(TemplateView):
    """
    Главная страница интернет-магазина
    """
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Рекомендуемые товары
        featured_products = Product.objects.filter(
            is_active=True,
            is_featured=True
        ).select_related('category', 'brand').prefetch_related('images')[:12]
        
        # Новые поступления
        new_arrivals = Product.objects.filter(
            is_active=True
        ).order_by('-created_at').select_related('category', 'brand')[:8]
        
        # Хиты продаж
        bestsellers = Product.objects.filter(
            is_active=True
        ).order_by('-sales_count').select_related('category', 'brand')[:8]
        
        # Товары со скидкой
        discounted_products = Product.objects.filter(
            is_active=True,
            old_price__isnull=False
        ).select_related('category', 'brand')[:8]
        
        # Популярные категории
        popular_categories = Category.objects.filter(
            is_active=True
        ).annotate(
            product_count=Count('products'),
            avg_price=Avg('products__price')
        ).order_by('-product_count')[:8]
        
        # Популярные бренды
        popular_brands = Brand.objects.filter(
            is_active=True
        ).annotate(
            products_count=Count('products')
        ).order_by('-products_count')[:8]
        
        # Новости блога
        latest_articles = Article.objects.filter(
            is_published=True,
            published_at__lte=timezone.now()
        ).select_related('category', 'author')[:6]
        
        # Статистика для сайта
        stats = {
            'total_products': Product.objects.filter(is_active=True).count(),
            'total_categories': Category.objects.filter(is_active=True).count(),
            'total_brands': Brand.objects.filter(is_active=True).count(),
        }
        
        # Количество товаров в корзине для неавторизованного пользователя
        cart_items_count = 0
        if self.request.session.session_key:
            try:
                cart = Cart.objects.get(session_key=self.request.session.session_key, user=None)
                cart_items_count = cart.items_count
            except Cart.DoesNotExist:
                pass
        
        context.update({
            'featured_products': featured_products,
            'new_arrivals': new_arrivals,
            'bestsellers': bestsellers,
            'discounted_products': discounted_products,
            'popular_categories': popular_categories,
            'popular_brands': popular_brands,
            'latest_articles': latest_articles,
            'stats': stats,
            'cart_items_count': cart_items_count,
        })
        
        return context

def about(request):
    """
    Страница "О нас"
    """
    return render(request, 'core/about.html')

def contact(request):
    """
    Страница контактов
    """
    if request.method == 'POST':
        # Обработка формы обратной связи
        pass
    
    return render(request, 'core/contact.html')

def delivery(request):
    """
    Страница доставки
    """
    return render(request, 'core/delivery.html')

def payment(request):
    """
    Страница оплаты
    """
    return render(request, 'core/payment.html')

def returns(request):
    """
    Страница возвратов
    """
    return render(request, 'core/returns.html')

def privacy(request):
    """
    Политика конфиденциальности
    """
    return render(request, 'core/privacy.html')

def terms(request):
    """
    Условия использования
    """
    return render(request, 'core/terms.html')

def sitemap(request):
    """
    Карта сайта
    """
    context = {
        'categories': Category.objects.filter(is_active=True),
        'brands': Brand.objects.filter(is_active=True),
        'products': Product.objects.filter(is_active=True),
        'articles': Article.objects.filter(is_published=True),
    }
    return render(request, 'core/sitemap.html', context)

# Placeholder для страницы магазина
def shop(request):
    """Перенаправление на каталог товаров"""
    from django.shortcuts import redirect
    return redirect('catalog:product_list')
