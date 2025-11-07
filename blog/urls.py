"""
URL маршруты для приложения blog (блог и новости)
"""

from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    # Основные страницы
    path('', views.article_list, name='post_list'),
    path('post/<slug:slug>/', views.article_detail, name='post_detail'),
    path('category/<slug:slug>/', views.category_detail, name='category_posts'),
    path('tag/<slug:slug>/', views.tag_detail, name='tag_posts'),
    path('search/', views.article_search, name='blog_search'),
    
    # Управление постами (для авторизованных)
    path('create/', views.article_create, name='create_post'),
    path('edit/<slug:slug>/', views.article_edit, name='edit_post'),
    path('delete/<slug:slug>/', views.article_delete, name='delete_post'),
    
    # Комментарии
    path('post/<slug:slug>/comment/', views.add_comment, name='add_comment'),
    path('newsletter/', views.newsletter_signup, name='newsletter_signup'),
    path('my-articles/', views.my_articles, name='my_articles'),
    path('comments/', views.comments_list, name='comments_list'),
    
    # Категории и теги
    path('categories/', views.category_list, name='category_list'),
    path('tags/', views.tag_list, name='tag_list'),
    
    # RSS и архивы
    path('rss/', views.blog_rss, name='blog_rss'),
    path('archive/', views.post_archive, name='post_archive'),
    
    # Популярные и избранные
    path('popular/', views.popular_posts, name='popular_posts'),
    path('featured/', views.featured_posts, name='featured_posts'),
]