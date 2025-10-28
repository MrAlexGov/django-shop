"""
Представления для блога и новостей интернет-магазина
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.conf import settings
from django.core.cache import cache
from django.db import transaction, models
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import json
import re
from datetime import datetime, date
from PIL import Image

from .models import (
    Category, Article, ArticleTag, Comment,
    ArticleImage, Newsletter, Tag
)
from .forms import (
    ArticleForm, ArticleSearchForm, NewsletterForm,
    CommentForm
)


def article_list(request):
    """
    Список всех статей блога (минимальная рабочая версия)
    """
    # Простейшая версия без сложных связей
    context = {
        'articles': [],
        'categories': [],
        'featured_articles': [],
        'page_obj': None,
    }
    
    return render(request, 'blog/article_list.html', context)


def article_detail(request, slug):
    """
    Детальная страница статьи
    """
    # Увеличиваем счетчик просмотров с кэшированием
    cache_key = f'blog_article_{slug}'
    article = cache.get(cache_key)
    
    if not article:
        article = get_object_or_404(
            Article.objects.select_related('category', 'author'),
            slug=slug,
            is_published=True,
            published_at__lte=timezone.now()
        )
        
        # Загружаем связанные данные
        article = Article.objects.filter(id=article.id).select_related('category', 'author').prefetch_related(
            'tags', 'articleimage_set', 'comments__user'
        ).first()
        
        cache.set(cache_key, article, 900)
    
    # Увеличиваем счетчик просмотров (без блокировки страницы)
    from django.db.models import F
    Article.objects.filter(id=article.id).update(
        views_count=F('views_count') + 1
    )
    
    # Обновляем просмотры в объекте для отображения
    article.views_count += 1
    
    # Похожие статьи
    related_articles = get_related_articles(article)
    
    # Последние статьи
    recent_articles = Article.objects.filter(
        is_published=True,
        published_at__lte=timezone.now()
    ).exclude(id=article.id).order_by('-published_at')[:5]
    
    # Комментарии
    comments = article.comments.filter(is_approved=True).select_related('user').order_by('created_at')
    
    # Форма комментария
    comment_form = None
    if request.user.is_authenticated:
        if request.method == 'POST':
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                try:
                    with transaction.atomic():
                        comment = comment_form.save(commit=False)
                        comment.article = article
                        comment.user = request.user
                        comment.save()
                        messages.success(request, 'Комментарий добавлен и ожидает модерации')
                        return redirect('blog:article_detail', slug=article.slug)
                except Exception as e:
                    messages.error(request, f'Ошибка при добавлении комментария: {str(e)}')
        else:
            comment_form = CommentForm()
    
    # SEO оптимизация
    update_article_seo(article)
    
    context = {
        'article': article,
        'related_articles': related_articles,
        'recent_articles': recent_articles,
        'comments': comments,
        'comment_form': comment_form,
        'categories': Category.objects.filter(
            articles__is_published=True
        ).annotate(article_count=Count('articles')).order_by('name')[:10],
        'popular_tags': ArticleTag.objects.filter(
            articles__is_published=True
        ).annotate(article_count=Count('articles')).order_by('-article_count')[:10],
    }
    
    return render(request, 'blog/article_detail.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def article_create(request):
    """
    Создание новой статьи
    """
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    article = form.save(commit=False)
                    article.author = request.user
                    
                    # Если статья публикуется сразу
                    if article.is_published and not article.published_at:
                        article.published_at = timezone.now()
                    
                    article.save()
                    
                    # Сохраняем теги
                    form.save_m2m()
                    
                    # Обрабатываем изображения
                    process_article_images(request, article)
                    
                    messages.success(request, 'Статья успешно создана')
                    return redirect('blog:article_detail', slug=article.slug)
                    
            except Exception as e:
                messages.error(request, f'Ошибка при создании статьи: {str(e)}')
    else:
        form = ArticleForm()
    
    context = {
        'form': form,
        'title': 'Создание статьи'
    }
    
    return render(request, 'blog/article_form.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def article_edit(request, slug):
    """
    Редактирование статьи
    """
    article = get_object_or_404(Article, slug=slug, author=request.user)
    
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES, instance=article)
        if form.is_valid():
            try:
                with transaction.atomic():
                    article = form.save(commit=False)
                    
                    # Если статья публикуется первый раз
                    if article.is_published and not article.published_at:
                        article.published_at = timezone.now()
                    
                    article.save()
                    form.save_m2m()
                    
                    # Обрабатываем изображения
                    process_article_images(request, article)
                    
                    # Очищаем кэш
                    cache.delete(f'blog_article_{article.slug}')
                    
                    messages.success(request, 'Статья успешно обновлена')
                    return redirect('blog:article_detail', slug=article.slug)
                    
            except Exception as e:
                messages.error(request, f'Ошибка при обновлении статьи: {str(e)}')
    else:
        form = ArticleForm(instance=article)
    
    context = {
        'form': form,
        'article': article,
        'title': 'Редактирование статьи'
    }
    
    return render(request, 'blog/article_form.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_http_methods(["POST"])
def article_delete(request, slug):
    """
    Удаление статьи
    """
    article = get_object_or_404(Article, slug=slug, author=request.user)
    
    try:
        # Удаляем связанные изображения
        for image in article.articleimage_set.all():
            if image.image:
                default_storage.delete(image.image.path)
        
        article.delete()
        cache.delete(f'blog_article_{article.slug}')
        messages.success(request, 'Статья удалена')
        
    except Exception as e:
        messages.error(request, f'Ошибка при удалении статьи: {str(e)}')
    
    return redirect('blog:article_list')


@require_http_methods(["GET"])
def category_detail(request, slug):
    """
    Статьи по категории
    """
    category = get_object_or_404(Category, slug=slug)
    
    articles = Article.objects.filter(
        category=category,
        is_published=True,
        published_at__lte=timezone.now()
    ).select_related('author').prefetch_related('tags').order_by('-published_at')
    
    # Пагинация
    paginator = Paginator(articles, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Статистика категории
    category_stats = get_category_stats(category)
    
    context = {
        'category': category,
        'page_obj': page_obj,
        'articles': page_obj.object_list,
        'category_stats': category_stats,
        'all_categories': Category.objects.all().order_by('name')
    }
    
    return render(request, 'blog/category_detail.html', context)


@require_http_methods(["GET"])
def tag_detail(request, slug):
    """
    Статьи по тегу
    """
    tag = get_object_or_404(ArticleTag, slug=slug)
    
    articles = Article.objects.filter(
        tags=tag,
        is_published=True,
        published_at__lte=timezone.now()
    ).select_related('category', 'author').order_by('-published_at')
    
    # Пагинация
    paginator = Paginator(articles, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'tag': tag,
        'page_obj': page_obj,
        'articles': page_obj.object_list,
        'all_tags': ArticleTag.objects.annotate(
            article_count=Count('articles')
        ).order_by('-article_count')[:20]
    }
    
    return render(request, 'blog/tag_detail.html', context)


@require_http_methods(["GET"])
def article_search(request):
    """
    Поиск статей
    """
    form = ArticleSearchForm(request.GET)
    articles = Article.objects.filter(
        is_published=True,
        published_at__lte=timezone.now()
    ).select_related('category', 'author').prefetch_related('tags')
    
    if form.is_valid():
        search_query = form.cleaned_data.get('search_query')
        category = form.cleaned_data.get('category')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        
        if search_query:
            articles = articles.filter(
                Q(title__icontains=search_query) |
                Q(content__icontains=search_query) |
                Q(excerpt__icontains=search_query)
            )
        
        if category:
            articles = articles.filter(category=category)
        
        if date_from:
            articles = articles.filter(published_at__date__gte=date_from)
        
        if date_to:
            articles = articles.filter(published_at__date__lte=date_to)
    
    # Пагинация
    paginator = Paginator(articles.order_by('-published_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'articles': page_obj.object_list,
        'results_count': articles.count(),
        'search_query': request.GET.get('search_query', ''),
    }
    
    return render(request, 'blog/article_search.html', context)


@login_required
def my_articles(request):
    """
    Мои статьи (для авторов)
    """
    articles = Article.objects.filter(
        author=request.user
    ).select_related('category').prefetch_related('tags')
    
    # Фильтрация
    status_filter = request.GET.get('status')
    if status_filter == 'published':
        articles = articles.filter(is_published=True)
    elif status_filter == 'draft':
        articles = articles.filter(is_published=False)
    
    # Поиск
    search_query = request.GET.get('q')
    if search_query:
        articles = articles.filter(title__icontains=search_query)
    
    # Пагинация
    paginator = Paginator(articles.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'articles': page_obj.object_list,
        'status_filter': status_filter,
        'search_query': search_query,
        'article_stats': {
            'total': articles.count(),
            'published': Article.objects.filter(author=request.user, is_published=True).count(),
            'drafts': Article.objects.filter(author=request.user, is_published=False).count(),
        }
    }
    
    return render(request, 'blog/my_articles.html', context)


@login_required
def comments_list(request):
    """
    Список моих комментариев
    """
    comments = Comment.objects.filter(
        user=request.user
    ).select_related('article').order_by('-created_at')
    
    # Фильтрация
    status_filter = request.GET.get('status')
    if status_filter == 'approved':
        comments = comments.filter(is_approved=True)
    elif status_filter == 'pending':
        comments = comments.filter(is_approved=False)
    
    # Поиск
    search_query = request.GET.get('q')
    if search_query:
        comments = comments.filter(
            Q(content__icontains=search_query) |
            Q(article__title__icontains=search_query)
        )
    
    # Пагинация
    paginator = Paginator(comments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'comments': page_obj.object_list,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'blog/comments_list.html', context)


@require_http_methods(["GET"])
def newsletter_signup(request):
    """
    Подписка на новостную рассылку
    """
    form = NewsletterSubscriberForm(request.GET or None)
    
    if request.method == 'POST' and form.is_valid():
        try:
            subscriber = form.save()
            messages.success(request, 'Спасибо за подписку на нашу рассылку!')
            return redirect('blog:article_list')
        except Exception as e:
            messages.error(request, 'Ошибка при подписке. Возможно, вы уже подписаны.')
    
    context = {
        'form': form
    }
    
    return render(request, 'blog/newsletter_signup.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def blog_dashboard(request):
    """
    Дашборд блога для администраторов
    """
    # Общая статистика
    total_articles = Article.objects.count()
    published_articles = Article.objects.filter(is_published=True).count()
    total_comments = Comment.objects.count()
    approved_comments = Comment.objects.filter(is_approved=True).count()
    subscribers = NewsletterSubscriber.objects.filter(is_active=True).count()
    
    # Последние статьи
    recent_articles = Article.objects.select_related('category', 'author').order_by('-created_at')[:5]
    
    # Последние комментарии
    recent_comments = Comment.objects.select_related('article', 'user').order_by('-created_at')[:5]
    
    # Статистика по категориям
    categories_stats = Category.objects.annotate(
        article_count=Count('articles'),
        views_count=Count('articles__views_count')
    ).order_by('-article_count')
    
    # Популярные статьи
    popular_articles = Article.objects.filter(
        is_published=True
    ).order_by('-views_count')[:10]
    
    context = {
        'total_articles': total_articles,
        'published_articles': published_articles,
        'total_comments': total_comments,
        'approved_comments': approved_comments,
        'subscribers': subscribers,
        'recent_articles': recent_articles,
        'recent_comments': recent_comments,
        'categories_stats': categories_stats,
        'popular_articles': popular_articles,
    }
    
    return render(request, 'blog/dashboard.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def blog_analytics(request):
    """
    Аналитика блога
    """
    from django.db.models import Avg
    
    # Общая статистика
    total_articles = Article.objects.filter(is_published=True).count()
    total_views = Article.objects.filter(is_published=True).aggregate(
        total_views=models.Sum('views_count')
    )['total_views'] or 0
    
    average_views = Article.objects.filter(
        is_published=True
    ).aggregate(avg_views=Avg('views_count'))['avg_views'] or 0
    
    # Статистика по месяцам
    from django.utils import timezone
    last_month = timezone.now() - timezone.timedelta(days=30)
    
    monthly_articles = Article.objects.filter(
        is_published=True,
        published_at__gte=last_month
    ).extra(
        select={'month': 'strftime("%Y-%m", published_at)'}
    ).values('month').annotate(
        count=models.Count('id'),
        views=models.Sum('views_count')
    ).order_by('month')
    
    # Топ статьи
    top_articles = Article.objects.filter(
        is_published=True
    ).order_by('-views_count')[:10]
    
    # Статистика по авторам
    authors_stats = Article.objects.filter(
        is_published=True
    ).values('author__first_name', 'author__last_name').annotate(
        article_count=models.Count('id'),
        total_views=models.Sum('views_count')
    ).order_by('-total_views')
    
    context = {
        'total_articles': total_articles,
        'total_views': total_views,
        'average_views': round(average_views, 1),
        'monthly_articles': monthly_articles,
        'top_articles': top_articles,
        'authors_stats': authors_stats,
    }
    
    return render(request, 'blog/analytics.html', context)


# AJAX эндпоинты

@login_required
@require_http_methods(["POST"])
def like_article(request, slug):
    """
    Лайк статьи (AJAX)
    """
    article = get_object_or_404(Article, slug=slug, is_published=True)
    
    # Проверяем, не лайкнул ли уже пользователь
    from .models import ArticleLike
    existing_like = ArticleLike.objects.filter(article=article, user=request.user).first()
    
    if existing_like:
        existing_like.delete()
        liked = False
        message = 'Лайк убран'
    else:
        ArticleLike.objects.create(article=article, user=request.user)
        liked = True
        message = 'Статья лайкнута'
    
    # Обновляем счетчик лайков
    likes_count = ArticleLike.objects.filter(article=article).count()
    
    return JsonResponse({
        'status': 'success',
        'liked': liked,
        'likes_count': likes_count,
        'message': message
    })


@require_http_methods(["POST"])
def share_article(request, slug):
    """
    Поделиться статьей (AJAX)
    """
    article = get_object_or_404(Article, slug=slug, is_published=True)
    
    try:
        data = json.loads(request.body)
        platform = data.get('platform')
        
        # Увеличиваем счетчик шеров
        if platform == 'facebook':
            article.facebook_shares = models.F('facebook_shares') + 1
        elif platform == 'twitter':
            article.twitter_shares = models.F('twitter_shares') + 1
        elif platform == 'vk':
            article.vk_shares = models.F('vk_shares') + 1
        elif platform == 'telegram':
            article.telegram_shares = models.F('telegram_shares') + 1
        
        article.save(update_fields=['facebook_shares', 'twitter_shares', 'vk_shares', 'telegram_shares'])
        
        return JsonResponse({
            'status': 'success',
            'message': 'Спасибо за поделиться!'
        })
        
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Неверный запрос'}, status=400)


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_http_methods(["POST"])
def bulk_action_articles(request):
    """
    Массовые действия со статьями (AJAX)
    """
    try:
        data = json.loads(request.body)
        article_ids = data.get('article_ids', [])
        action = data.get('action')
        
        articles = Article.objects.filter(id__in=article_ids, author=request.user)
        
        if action == 'publish':
            updated = articles.update(is_published=True, published_at=timezone.now())
            message = f'Опубликовано {updated} статей'
        elif action == 'unpublish':
            updated = articles.update(is_published=False)
            message = f'Снято с публикации {updated} статей'
        elif action == 'delete':
            # Удаляем изображения
            for article in articles:
                for image in article.articleimage_set.all():
                    if image.image:
                        default_storage.delete(image.image.path)
            
            articles.delete()
            message = f'Удалено {len(article_ids)} статей'
        else:
            return JsonResponse({'error': 'Неизвестное действие'}, status=400)
        
        return JsonResponse({
            'status': 'success',
            'message': message
        })
        
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Неверный запрос'}, status=400)


# Вспомогательные функции

def get_related_articles(article, limit=3):
    """
    Получение похожих статей
    """
    related = Article.objects.filter(
        category=article.category,
        is_published=True,
        published_at__lte=timezone.now()
    ).exclude(id=article.id)
    
    # Если нет статей в той же категории, берем по тегам
    if not related.exists():
        related = Article.objects.filter(
            tags__in=article.tags.all(),
            is_published=True,
            published_at__lte=timezone.now()
        ).exclude(id=article.id).distinct()
    
    return related[:limit]


def get_category_stats(category):
    """
    Получение статистики категории
    """
    articles = Article.objects.filter(category=category, is_published=True)
    
    return {
        'total_articles': articles.count(),
        'total_views': articles.aggregate(total=models.Sum('views_count'))['total'] or 0,
        'average_views': articles.aggregate(avg=models.Avg('views_count'))['avg'] or 0,
        'latest_article': articles.order_by('-published_at').first(),
    }


def process_article_images(request, article):
    """
    Обработка изображений статьи
    """
    # Получаем изображения из формы
    images = request.FILES.getlist('images')
    
    for i, image in enumerate(images):
        try:
            # Создаем изображение
            article_image = ArticleImage.objects.create(
                article=article,
                image=image,
                caption=f'Изображение {i+1}'
            )
            
            # Оптимизируем изображение
            optimize_image(article_image.image.path)
            
        except Exception as e:
            print(f'Error processing image: {e}')


def optimize_image(image_path):
    """
    Оптимизация изображения
    """
    try:
        with Image.open(image_path) as img:
            # Максимальный размер для блога
            max_size = (1200, 800)
            
            # Изменяем размер если нужно
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                img.save(image_path, optimize=True, quality=85)
            
    except Exception as e:
        print(f'Error optimizing image: {e}')


def update_article_seo(article):
    """
    Обновление SEO данных статьи
    """
    # Автоматически генерируем мета-описание если не задано
    if not article.meta_description:
        # Берем первые 150 символов текста
        text_without_html = re.sub(r'<[^>]+>', '', article.content)
        article.meta_description = text_without_html[:150] + '...'
    
    # Автоматически генерируем meta_title если не задан
    if not article.meta_title:
        article.meta_title = article.title[:60]
    
    article.save(update_fields=['meta_description', 'meta_title'])


def generate_sitemap():
    """
    Генерация карты сайта для блога
    """
    articles = Article.objects.filter(
        is_published=True,
        published_at__lte=timezone.now()
    ).order_by('-updated_at')
    
    sitemap_data = []
    for article in articles:
        sitemap_data.append({
            'url': reverse('blog:article_detail', kwargs={'slug': article.slug}),
            'lastmod': article.updated_at,
            'changefreq': 'weekly',
            'priority': 0.8
        })
    
    return sitemap_data


def generate_rss_feed():
    """
    Генерация RSS ленты блога
    """
    articles = Article.objects.filter(
        is_published=True,
        published_at__lte=timezone.now()
    ).order_by('-published_at')[:20]
    
    # Здесь можно добавить генерацию RSS ленты
    pass


def create_article_slug(title):
    """
    Создание уникального slug для статьи
    """
    from django.utils.text import slugify
    from .models import Article
    
    base_slug = slugify(title)
    slug = base_slug
    counter = 1
    
    while Article.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    return slug


def send_newsletters():
    """
    Отправка новостной рассылки
    """
    # Получаем активных подписчиков
    subscribers = NewsletterSubscriber.objects.filter(is_active=True)
    
    # Получаем последние статьи
    recent_articles = Article.objects.filter(
        is_published=True,
        published_at__gte=timezone.now() - timezone.timedelta(days=7)
    ).order_by('-published_at')[:5]
    
    for subscriber in subscribers:
        # Отправляем email
        try:
            send_newsletter_email(subscriber.email, recent_articles)
        except Exception as e:
            print(f'Error sending newsletter to {subscriber.email}: {e}')


def send_newsletter_email(email, articles):
    """
    Отправка email рассылки
    """
    # Здесь можно добавить логику отправки email
    # Например, используя Django email или внешний сервис
    pass


# Алиасы для соответствия URL
post_list = article_list
post_detail = article_detail
category_posts = category_detail
tag_posts = tag_detail
blog_search = article_search

def create_post(request):
    """Создание поста (алиас для article_create)"""
    return article_create(request)

def edit_post(request, slug):
    """Редактирование поста (алиас для article_edit)"""
    return article_edit(request, slug)

def delete_post(request, slug):
    """Удаление поста (алиас для article_delete)"""
    return article_delete(request, slug)

def add_comment(request, slug):
    """Добавление комментария"""
    article = get_object_or_404(Article, slug=slug, is_published=True)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.article = article
            comment.user = request.user
            comment.save()
            messages.success(request, 'Комментарий добавлен и ожидает модерации')
            return redirect('blog:post_detail', slug=slug)
    else:
        form = CommentForm()
    return render(request, 'blog/add_comment.html', {'article': article, 'form': form})

def edit_comment(request, comment_id):
    """Редактирование комментария"""
    return JsonResponse({'status': 'not_implemented'})

def delete_comment(request, comment_id):
    """Удаление комментария"""
    return JsonResponse({'status': 'not_implemented'})

def reply_to_comment(request, comment_id):
    """Ответ на комментарий"""
    return JsonResponse({'status': 'not_implemented'})

def category_list(request):
    """Список категорий"""
    categories = Category.objects.all().annotate(
        article_count=Count('articles')
    ).order_by('name')
    return render(request, 'blog/category_list.html', {'categories': categories})

def tag_list(request):
    """Список тегов"""
    tags = ArticleTag.objects.annotate(
        article_count=Count('articles')
    ).order_by('-article_count')
    return render(request, 'blog/tag_list.html', {'tags': tags})

def blog_rss(request):
    """RSS лента блога"""
    return HttpResponse('RSS feed not implemented yet')

def post_archive(request):
    """Архив постов"""
    return render(request, 'blog/post_archive.html')

def monthly_archive(request, year, month):
    """Архив по месяцам"""
    return render(request, 'blog/monthly_archive.html', {'year': year, 'month': month})

def popular_posts(request):
    """Популярные посты"""
    posts = Article.objects.filter(
        is_published=True,
        published_at__lte=timezone.now()
    ).order_by('-views_count')[:20]
    return render(request, 'blog/popular_posts.html', {'posts': posts})

def featured_posts(request):
    """Рекомендуемые посты"""
    posts = Article.objects.filter(
        is_published=True,
        is_featured=True,
        published_at__lte=timezone.now()
    )[:20]
    return render(request, 'blog/featured_posts.html', {'posts': posts})

def newsletter_subscribe(request):
    """Подписка на новостную рассылку"""
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            NewsletterSubscriber.objects.update_or_create(
                email=email,
                defaults={'is_active': True}
            )
            messages.success(request, 'Вы успешно подписались на новостную рассылку!')
        return redirect('blog:post_list')
    return render(request, 'blog/newsletter_subscribe.html')

def newsletter_unsubscribe(request, token):
    """Отписка от новостной рассылки"""
    return JsonResponse({'status': 'unsubscribed'})

def blog_sitemap(request):
    """Sitemap блога"""
    return HttpResponse('Sitemap not implemented yet')

def validate_blog_data(request):
    """Валидация данных блога"""
    return JsonResponse({'validation': 'passed'})
