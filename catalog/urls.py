"""
URL маршруты для приложения catalog (каталог товаров)
"""

from django.urls import path, include
from django.views.generic import TemplateView
from . import views

app_name = 'catalog'

urlpatterns = [
    # Главная страница каталога
    path('', views.product_list, name='product_list'),
    
    # Категории
    path('categories/', views.category_list, name='category_list'),
    path('categories/<slug:slug>/', views.category_detail, name='category_detail'),
    path('categories/<slug:slug>/products/', views.category_products, name='category_products'),
    
    # Бренды
    path('brands/', views.brand_list, name='brand_list'),
    path('brands/<slug:slug>/', views.brand_detail, name='brand_detail'),
    path('brands/<slug:slug>/products/', views.brand_products, name='brand_products'),
    
    # Товары
    path('products/', views.product_list, name='product_list'),
    path('products/<slug:slug>/', views.product_detail, name='product_detail'),
    path('products/<slug:slug>/images/', views.product_images, name='product_images'),
    path('products/<slug:slug>/reviews/', views.product_reviews, name='product_reviews'),
    path('products/<slug:slug>/specifications/', views.product_specifications, name='product_specifications'),
    path('products/<slug:slug>/related/', views.related_products, name='related_products'),
    path('products/<slug:slug>/availability/', views.product_availability, name='product_availability'),
    
    # Отзывы
    path('reviews/', views.review_list, name='review_list'),
    path('reviews/add/', views.add_review, name='add_review'),
    path('reviews/<int:review_id>/edit/', views.edit_review, name='edit_review'),
    path('reviews/<int:review_id>/delete/', views.delete_review, name='delete_review'),
    path('reviews/<int:review_id>/helpful/', views.mark_review_helpful, name='mark_review_helpful'),
    
    # Поиск
    path('search/', views.search_products, name='search_products'),
    path('search/suggestions/', views.search_suggestions, name='search_suggestions'),
    path('search/popular/', views.popular_searches, name='popular_searches'),
    
    # Фильтрация
    path('filter/', views.filter_products, name='filter_products'),
    path('filter/categories/', views.filter_by_categories, name='filter_by_categories'),
    path('filter/brands/', views.filter_by_brands, name='filter_by_brands'),
    path('filter/price/', views.filter_by_price, name='filter_by_price'),
    path('filter/specifications/', views.filter_by_specifications, name='filter_by_specifications'),
    path('filter/availability/', views.filter_by_availability, name='filter_by_availability'),
    
    # Сортировка
    path('sort/', views.sort_products, name='sort_products'),
    path('sort/price/', views.sort_by_price, name='sort_by_price'),
    path('sort/popularity/', views.sort_by_popularity, name='sort_by_popularity'),
    path('sort/newest/', views.sort_by_newest, name='sort_by_newest'),
    path('sort/rating/', views.sort_by_rating, name='sort_by_rating'),
    
    # Сравнение товаров
    path('compare/', views.compare_products, name='compare_products'),
    path('compare/add/<slug:product_slug>/', views.add_to_compare, name='add_to_compare'),
    path('compare/remove/<slug:product_slug>/', views.remove_from_compare, name='remove_from_compare'),
    path('compare/clear/', views.clear_compare_list, name='clear_compare_list'),
    
    # Избранное
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/add/<slug:product_slug>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<slug:product_slug>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist/clear/', views.clear_wishlist, name='clear_wishlist'),
    
    # Характеристики
    path('specifications/', views.specification_list, name='specification_list'),
    path('specifications/<slug:slug>/', views.specification_detail, name='specification_detail'),
    
    # Статистика и аналитика
    path('statistics/', views.product_statistics, name='product_statistics'),
    path('statistics/trending/', views.trending_products, name='trending_products'),
    path('statistics/bestsellers/', views.bestsellers, name='bestsellers'),
    path('statistics/new-arrivals/', views.new_arrivals, name='new_arrivals'),
    path('statistics/sale/', views.on_sale_products, name='on_sale_products'),
    
    # Акции и предложения
    path('promotions/', views.promotions, name='promotions'),
    path('promotions/<slug:slug>/', views.promotion_detail, name='promotion_detail'),
    path('discounts/', views.discounts, name='discounts'),
    path('discounts/<slug:slug>/', views.discount_detail, name='discount_detail'),
    
    # Теги
    path('tags/', views.tag_list, name='tag_list'),
    path('tags/<slug:slug>/', views.tag_products, name='tag_products'),
    
    # Рекомендации
    path('recommendations/', views.recommendations, name='recommendations'),
    path('recommendations/personal/', views.personal_recommendations, name='personal_recommendations'),
    path('recommendations/similar/<slug:product_slug>/', views.similar_products, name='similar_products'),
    path('recommendations/bought-together/<slug:product_slug>/', views.bought_together, name='bought_together'),
    
    # Отложенные товары
    path('saved/', views.saved_products, name='saved_products'),
    path('saved/add/<slug:product_slug>/', views.add_to_saved, name='add_to_saved'),
    path('saved/remove/<slug:product_slug>/', views.remove_from_saved, name='remove_from_saved'),
    
    # Последние просмотры
    path('recently-viewed/', views.recently_viewed, name='recently_viewed'),
    
    # Сравнение по характеристикам
    path('compare/specifications/', views.compare_by_specifications, name='compare_by_specifications'),
    
    # Экспорт каталога
    path('export/csv/', views.export_catalog_csv, name='export_catalog_csv'),
    path('export/excel/', views.export_catalog_excel, name='export_catalog_excel'),
    path('export/xml/', views.export_catalog_xml, name='export_catalog_xml'),
    
    # Импорт товаров
    path('import/', views.import_products, name='import_products'),
    
    # API endpoints для AJAX
    path('api/product-quick-view/<slug:slug>/', views.api_product_quick_view, name='api_quick_view'),
    path('api/product-availability/<slug:slug>/', views.api_product_availability, name='api_product_availability'),
    path('api/add-to-cart/<slug:slug>/', views.api_add_to_cart, name='api_add_to_cart'),
    path('api/add-to-wishlist/<slug:slug>/', views.api_add_to_wishlist, name='api_add_to_wishlist'),
    path('api/add-to-compare/<slug:slug>/', views.api_add_to_compare, name='api_add_to_compare'),
    path('api/remove-from-wishlist/<slug:slug>/', views.api_remove_from_wishlist, name='api_remove_from_wishlist'),
    path('api/remove-from-compare/<slug:slug>/', views.api_remove_from_compare, name='api_remove_from_compare'),
    
    # Каталог в формате JSON для мобильного приложения
    path('api/products/', views.api_product_list, name='api_product_list'),
    path('api/products/<slug:slug>/', views.api_product_detail, name='api_product_detail'),
    path('api/categories/', views.api_category_list, name='api_category_list'),
    path('api/brands/', views.api_brand_list, name='api_brand_list'),
    path('api/search/', views.api_search, name='api_search'),
    path('api/filter/', views.api_filter, name='api_filter'),
    path('api/sort/', views.api_sort, name='api_sort'),
    path('api/reviews/', views.api_review_list, name='api_review_list'),
    path('api/reviews/add/', views.api_add_review, name='api_add_review'),
    
    # Интеграция с внешними системами
    path('feed/yandex-market/', views.yandex_market_feed, name='yandex_market_feed'),
    path('feed/ozon/', views.ozon_feed, name='ozon_feed'),
    path('feed/wildberries/', views.wildberries_feed, name='wildberries_feed'),
    
    # SEO и sitemap
    path('sitemap-products.xml', views.product_sitemap, name='product_sitemap'),
    path('sitemap-categories.xml', views.category_sitemap, name='category_sitemap'),
    path('sitemap-brands.xml', views.brand_sitemap, name='brand_sitemap'),
    
    # Роутер для SPA (Single Page Application)
    path('spa/<path:path>/', views.spa_catalog, name='spa_catalog'),
]