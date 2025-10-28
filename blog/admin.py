"""
Административная панель для приложения blog
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Category, Article, ArticleImage, Tag, ArticleTag, Comment, CommentLike, Newsletter, NewsletterSubscriber, ArticleLike, NewsletterCampaign


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Category
    """
    list_display = (
        'name', 'image_preview', 'is_active', 
        'articles_count', 'sort_order', 'created_at'
    )
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'image')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Настройки', {
            'fields': ('is_active', 'sort_order')
        }),
    )
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: auto;">',
                obj.image.url
            )
        return "Нет изображения"
    image_preview.short_description = 'Изображение'
    
    def articles_count(self, obj):
        return obj.articles_count
    articles_count.short_description = 'Статей'


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Article
    """
    list_display = (
        'title', 'author', 'category', 'is_published',
        'is_featured', 'is_important', 'views_count',
        'published_at', 'created_at'
    )
    list_filter = (
        'is_published', 'is_featured', 'is_important',
        'category', 'published_at', 'created_at'
    )
    search_fields = ('title', 'subtitle', 'excerpt', 'content')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = (
        'views_count', 'likes_count', 'comments_count',
        'published_at', 'created_at', 'updated_at'
    )
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'slug', 'subtitle', 'author', 'category')
        }),
        ('Контент', {
            'fields': ('excerpt', 'content', 'featured_image')
        }),
        ('Мета-информация', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Настройки публикации', {
            'fields': ('is_published', 'is_featured', 'is_important', 'published_at')
        }),
        ('Статистика', {
            'fields': ('views_count', 'likes_count', 'comments_count'),
            'classes': ('collapse',)
        }),
        ('Настройки отображения', {
            'fields': ('sort_order',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['publish_selected', 'mark_as_featured', 'export_articles_csv']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('author', 'category')
    
    def publish_selected(self, request, queryset):
        """Опубликовать выбранные статьи"""
        updated = queryset.update(is_published=True)
        self.message_user(request, f'{updated} статей опубликованы.')
    publish_selected.short_description = 'Опубликовать выбранные'
    
    def mark_as_featured(self, request, queryset):
        """Отметить как рекомендуемые"""
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} статей отмечены как рекомендуемые.')
    mark_as_featured.short_description = 'Отметить как рекомендуемые'
    
    def export_articles_csv(self, request, queryset):
        """Экспорт статей в CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="articles.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Название', 'Автор', 'Категория', 'Опубликовано', 'Просмотры'])
        
        for article in queryset:
            writer.writerow([
                article.title,
                article.author.get_full_name(),
                article.category.name,
                'Да' if article.is_published else 'Нет',
                article.views_count
            ])
        
        return response
    export_articles_csv.short_description = 'Экспортировать в CSV'


@admin.register(ArticleImage)
class ArticleImageAdmin(admin.ModelAdmin):
    """
    Административная панель для модели ArticleImage
    """
    list_display = (
        'article', 'image_preview', 'caption', 'alt_text',
        'sort_order', 'created_at'
    )
    list_filter = ('created_at',)
    search_fields = ('article__title', 'caption', 'alt_text')
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: auto;">',
                obj.image.url
            )
        return "Нет изображения"
    image_preview.short_description = 'Изображение'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('article')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Tag
    """
    list_display = (
        'name', 'articles_count', 'created_at'
    )
    list_filter = ('created_at',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    
    def articles_count(self, obj):
        return obj.articles_count
    articles_count.short_description = 'Статей'


@admin.register(ArticleTag)
class ArticleTagAdmin(admin.ModelAdmin):
    """
    Административная панель для модели ArticleTag
    """
    list_display = ('article', 'tag', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('article__title', 'tag__name')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('article', 'tag')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Comment
    """
    list_display = (
        'article', 'get_author_name', 'status', 'is_spam',
        'likes_count', 'created_at'
    )
    list_filter = (
        'status', 'is_spam', 'created_at', 'parent'
    )
    search_fields = (
        'article__title', 'user__username', 'guest_name',
        'guest_email', 'content'
    )
    readonly_fields = (
        'likes_count', 'dislikes_count', 
        'created_at', 'updated_at'
    )
    
    def get_author_name(self, obj):
        return obj.get_author_name()
    get_author_name.short_description = 'Автор'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('article', 'user')


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    """
    Административная панель для модели CommentLike
    """
    list_display = ('comment', 'user', 'is_like', 'created_at')
    list_filter = ('is_like', 'created_at')
    search_fields = (
        'comment__article__title', 'user__username',
        'comment__user__username'
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('comment', 'comment__article', 'user')


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Newsletter
    """
    list_display = (
        'email', 'name', 'status', 'sent_count',
        'opened_count', 'clicked_count', 'subscribed_at'
    )
    list_filter = ('status', 'subscribed_at')
    search_fields = ('email', 'name')
    readonly_fields = (
        'sent_count', 'opened_count', 'clicked_count',
        'subscribed_at', 'unsubscribed_at', 'updated_at'
    )
    
    actions = ['activate_selected', 'ban_selected']
    
    def activate_selected(self, request, queryset):
        """Активировать выбранные подписки"""
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} подписок активировано.')
    activate_selected.short_description = 'Активировать выбранные'
    
    def ban_selected(self, request, queryset):
        """Заблокировать выбранные подписки"""
        updated = queryset.update(status='banned')
        self.message_user(request, f'{updated} подписок заблокировано.')
    ban_selected.short_description = 'Заблокировать выбранные'


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    """
    Административная панель для модели NewsletterSubscriber
    """
    list_display = (
        'email', 'name', 'is_active', 
        'subscribed_at', 'unsubscribed_at'
    )
    list_filter = ('is_active', 'subscribed_at')
    search_fields = ('email', 'name')
    readonly_fields = (
        'subscribed_at', 'unsubscribed_at'
    )
    
    actions = ['activate_selected', 'deactivate_selected']
    
    def activate_selected(self, request, queryset):
        """Активировать выбранных подписчиков"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} подписчиков активировано.')
    activate_selected.short_description = 'Активировать выбранных'
    
    def deactivate_selected(self, request, queryset):
        """Деактивировать выбранных подписчиков"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} подписчиков деактивировано.')
    deactivate_selected.short_description = 'Деактивировать выбранных'


@admin.register(ArticleLike)
class ArticleLikeAdmin(admin.ModelAdmin):
    """
    Административная панель для модели ArticleLike
    """
    list_display = ('article', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = (
        'article__title', 'user__username'
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('article', 'user')


@admin.register(NewsletterCampaign)
class NewsletterCampaignAdmin(admin.ModelAdmin):
    """
    Административная панель для модели NewsletterCampaign
    """
    list_display = (
        'subject', 'status', 'scheduled_at',
        'sent_at', 'total_recipients', 'sent_count',
        'opened_count', 'clicked_count', 'created_at'
    )
    list_filter = (
        'status', 'scheduled_at', 'sent_at', 'created_at'
    )
    search_fields = ('subject', 'content')
    readonly_fields = (
        'sent_count', 'opened_count', 'clicked_count', 'bounced_count',
        'created_at', 'updated_at'
    )
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('subject', 'content')
        }),
        ('Настройки отправки', {
            'fields': ('status', 'scheduled_at', 'sent_at')
        }),
        ('Целевая аудитория', {
            'fields': ('target_categories', 'target_tags')
        }),
        ('Статистика', {
            'fields': (
                'total_recipients', 'sent_count', 'opened_count',
                'clicked_count', 'bounced_count'
            ),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related()
    
    actions = ['schedule_campaign', 'mark_as_sent']
    
    def schedule_campaign(self, request, queryset):
        """Запланировать выбранные рассылки"""
        updated = queryset.update(status='scheduled')
        self.message_user(request, f'{updated} рассылок запланировано.')
    schedule_campaign.short_description = 'Запланировать выбранные'
    
    def mark_as_sent(self, request, queryset):
        """Отметить как отправленные"""
        updated = queryset.update(status='sent')
        self.message_user(request, f'{updated} рассылок отмечены как отправленные.')
    mark_as_sent.short_description = 'Отметить как отправленные'
