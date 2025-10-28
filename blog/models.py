"""
Модели блога/новостей для интернет-магазина
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone

User = get_user_model()


class Category(models.Model):
    """
    Категории статей в блоге
    """
    name = models.CharField('Название категории', max_length=100, unique=True)
    slug = models.SlugField('URL-идентификатор', max_length=100, unique=True)
    description = models.TextField('Описание', blank=True)
    image = models.ImageField('Изображение', upload_to='blog/categories/', null=True, blank=True)
    
    # Настройки отображения
    is_active = models.BooleanField('Активна', default=True)
    sort_order = models.PositiveIntegerField('Порядок сортировки', default=0)
    
    # SEO поля
    meta_title = models.CharField('Meta заголовок', max_length=60, blank=True)
    meta_description = models.CharField('Meta описание', max_length=160, blank=True)
    
    # Метаданные
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена', auto_now=True)
    
    class Meta:
        verbose_name = 'Категория блога'
        verbose_name_plural = 'Категории блога'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('blog:category_detail', kwargs={'slug': self.slug})
    
    @property
    def articles_count(self):
        return self.articles.filter(is_published=True).count()


class Article(models.Model):
    """
    Статьи/новости блога
    """
    # Основная информация
    title = models.CharField('Заголовок', max_length=200)
    slug = models.SlugField('URL-идентификатор', max_length=200, unique=True)
    subtitle = models.CharField('Подзаголовок', max_length=300, blank=True)
    
    # Связи
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_articles')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='articles')
    
    # Контент
    excerpt = models.TextField('Краткое описание (анонс)', max_length=500)
    content = models.TextField('Полный текст статьи')
    
    # Изображения
    featured_image = models.ImageField('Главное изображение', upload_to='blog/articles/', null=True, blank=True)
    gallery_images = models.ManyToManyField('ArticleImage', blank=True, related_name='articles')
    
    # Мета-информация
    meta_title = models.CharField('Meta заголовок', max_length=60, blank=True)
    meta_description = models.CharField('Meta описание', max_length=160, blank=True)
    meta_keywords = models.CharField('Meta ключевые слова', max_length=200, blank=True)
    
    # Настройки публикации
    is_published = models.BooleanField('Опубликовано', default=False)
    is_featured = models.BooleanField('Рекомендуемая статья', default=False)
    is_important = models.BooleanField('Важная новость', default=False)
    
    # Даты публикации
    published_at = models.DateTimeField('Дата публикации', null=True, blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    
    # Статистика
    views_count = models.PositiveIntegerField('Просмотры', default=0)
    likes_count = models.PositiveIntegerField('Лайки', default=0)
    comments_count = models.PositiveIntegerField('Комментарии', default=0)
    
    # Настройки отображения
    sort_order = models.PositiveIntegerField('Порядок сортировки', default=0)
    
    class Meta:
        verbose_name = 'Статья'
        verbose_name_plural = 'Статьи'
        ordering = ['-is_important', '-is_featured', '-published_at', '-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['-published_at']),
            models.Index(fields=['category', '-published_at']),
            models.Index(fields=['is_published', '-published_at']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        
        # Автоматически устанавливать дату публикации при первом включении
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        
        # Убирать дату публикации при выключении
        elif not self.is_published and self.published_at:
            self.published_at = None
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('blog:article_detail', kwargs={'slug': self.slug})
    
    def get_reading_time(self):
        """Подсчитать время чтения (200 слов в минуту)"""
        word_count = len(self.content.split())
        return max(1, round(word_count / 200))
    
    def is_recent(self):
        """Проверить, является ли статья недавней (менее 7 дней)"""
        if not self.published_at:
            return False
        days_since_published = (timezone.now() - self.published_at).days
        return days_since_published <= 7
    
    def increment_views(self):
        """Увеличить счетчик просмотров"""
        self.views_count += 1
        self.save(update_fields=['views_count'])
    
    def get_previous_article(self):
        """Получить предыдущую статью"""
        return Article.objects.filter(
            category=self.category,
            is_published=True,
            published_at__lt=self.published_at
        ).order_by('-published_at').first()
    
    def get_next_article(self):
        """Получить следующую статью"""
        return Article.objects.filter(
            category=self.category,
            is_published=True,
            published_at__gt=self.published_at
        ).order_by('published_at').first()


class ArticleImage(models.Model):
    """
    Изображения для статей
    """
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='article_images')
    image = models.ImageField('Изображение', upload_to='blog/articles/gallery/')
    caption = models.CharField('Подпись', max_length=200, blank=True)
    alt_text = models.CharField('Alt текст', max_length=100, blank=True)
    sort_order = models.PositiveIntegerField('Порядок сортировки', default=0)
    
    # Метаданные
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Изображение статьи'
        verbose_name_plural = 'Изображения статей'
        ordering = ['sort_order', 'created_at']
    
    def __str__(self):
        return f"{self.article.title} - {self.caption or 'Изображение'}"


class Tag(models.Model):
    """
    Теги для статей
    """
    name = models.CharField('Название тега', max_length=50, unique=True)
    slug = models.SlugField('URL-идентификатор', max_length=50, unique=True)
    description = models.TextField('Описание', blank=True)
    
    # Метаданные
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('blog:tag_detail', kwargs={'slug': self.slug})
    
    @property
    def articles_count(self):
        return self.articles.filter(is_published=True).count()


class ArticleTag(models.Model):
    """
    Связь статей с тегами
    """
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='tags')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='articles')
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Тег статьи'
        verbose_name_plural = 'Теги статей'
        unique_together = ('article', 'tag')
    
    def __str__(self):
        return f"{self.article.title} - {self.tag.name}"


class Comment(models.Model):
    """
    Комментарии к статьям
    """
    # Статусы комментариев
    STATUS_CHOICES = [
        ('pending', 'На модерации'),
        ('approved', 'Одобрен'),
        ('rejected', 'Отклонен'),
    ]
    
    # Основная информация
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_comments', null=True, blank=True)
    
    # Для анонимных комментариев
    guest_name = models.CharField('Имя гостя', max_length=100, blank=True)
    guest_email = models.EmailField('Email гостя', blank=True)
    
    # Контент комментария
    content = models.TextField('Текст комментария')
    
    # Статус модерации
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='pending')
    is_spam = models.BooleanField('Спам', default=False)
    
    # Ответ на другой комментарий
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    # Статистика
    likes_count = models.PositiveIntegerField('Лайки', default=0)
    dislikes_count = models.PositiveIntegerField('Дизлайки', default=0)
    
    # Метаданные
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    
    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ['-created_at']
    
    def __str__(self):
        author_name = self.user.get_full_name() if self.user else self.guest_name
        return f"{author_name} - {self.article.title}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Обновить счетчик комментариев в статье
        self.article.comments_count = self.article.comments.filter(status='approved').count()
        self.article.save(update_fields=['comments_count'])
    
    def delete(self, *args, **kwargs):
        article = self.article
        super().delete(*args, **kwargs)
        # Обновить счетчик комментариев в статье
        article.comments_count = article.comments.filter(status='approved').count()
        article.save(update_fields=['comments_count'])
    
    def get_author_name(self):
        """Получить имя автора комментария"""
        return self.user.get_full_name() if self.user else self.guest_name
    
    def get_author_email(self):
        """Получить email автора комментария"""
        return self.user.email if self.user else self.guest_email
    
    def can_edit(self, user):
        """Проверить, может ли пользователь редактировать комментарий"""
        return self.user == user or user.is_staff
    
    def can_delete(self, user):
        """Проверить, может ли пользователь удалить комментарий"""
        return self.can_edit(user)


class CommentLike(models.Model):
    """
    Лайки/дизлайки комментариев
    """
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comment_likes')
    is_like = models.BooleanField('Лайк (False = дизлайк)')
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Лайк комментария'
        verbose_name_plural = 'Лайки комментариев'
        unique_together = ('comment', 'user')
    
    def __str__(self):
        action = 'Лайк' if self.is_like else 'Дизлайк'
        return f"{action} - {self.user.get_full_name()} - {self.comment.id}"


class Newsletter(models.Model):
    """
    Подписка на новостную рассылку
    """
    STATUS_CHOICES = [
        ('active', 'Активна'),
        ('unsubscribed', 'Отписана'),
        ('banned', 'Заблокирована'),
    ]
    
    email = models.EmailField('Email', unique=True)
    name = models.CharField('Имя', max_length=100, blank=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Статистика
    sent_count = models.PositiveIntegerField('Отправлено писем', default=0)
    opened_count = models.PositiveIntegerField('Открыто писем', default=0)
    clicked_count = models.PositiveIntegerField('Кликов', default=0)
    
    # Метаданные
    subscribed_at = models.DateTimeField('Подписан', auto_now_add=True)
    unsubscribed_at = models.DateTimeField('Отписан', null=True, blank=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    
    class Meta:
        verbose_name = 'Подписка на новости'
        verbose_name_plural = 'Подписки на новости'
        ordering = ['-subscribed_at']
    
    def __str__(self):
        return f"{self.email} - {self.name}"
    
    def unsubscribe(self):
        """Отписать от рассылки"""
        self.status = 'unsubscribed'
        self.unsubscribed_at = timezone.now()
        self.save()
    
    def ban(self):
        """Заблокировать подписку"""
        self.status = 'banned'
        self.save()
    
    def activate(self):
        """Активировать подписку"""
        self.status = 'active'
        self.unsubscribed_at = None
        self.save()


class NewsletterSubscriber(models.Model):
    """
    Подписчики на новостную рассылку (упрощенная версия)
    """
    email = models.EmailField('Email', unique=True)
    name = models.CharField('Имя', max_length=100, blank=True)
    is_active = models.BooleanField('Активен', default=True)
    
    # Метаданные
    subscribed_at = models.DateTimeField('Подписан', auto_now_add=True)
    unsubscribed_at = models.DateTimeField('Отписан', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Подписчик рассылки'
        verbose_name_plural = 'Подписчики рассылки'
        ordering = ['-subscribed_at']
    
    def __str__(self):
        return self.email
    
    def unsubscribe(self):
        """Отписать от рассылки"""
        self.is_active = False
        self.unsubscribed_at = timezone.now()
        self.save()


class ArticleLike(models.Model):
    """
    Лайки статей
    """
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='article_likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='article_likes')
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Лайк статьи'
        verbose_name_plural = 'Лайки статей'
        unique_together = ('article', 'user')
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.article.title}"


class NewsletterCampaign(models.Model):
    """
    Рассылки новостей
    """
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('scheduled', 'Запланирована'),
        ('sending', 'Отправляется'),
        ('sent', 'Отправлена'),
        ('paused', 'Приостановлена'),
    ]
    
    subject = models.CharField('Тема письма', max_length=200)
    content = models.TextField('Содержимое письма')
    
    # Настройки отправки
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_at = models.DateTimeField('Запланировано на', null=True, blank=True)
    sent_at = models.DateTimeField('Отправлено', null=True, blank=True)
    
    # Целевая аудитория
    target_categories = models.ManyToManyField(Category, blank=True, related_name='newsletter_campaigns')
    target_tags = models.ManyToManyField(Tag, blank=True, related_name='newsletter_campaigns')
    
    # Статистика
    total_recipients = models.PositiveIntegerField('Получателей', default=0)
    sent_count = models.PositiveIntegerField('Отправлено', default=0)
    opened_count = models.PositiveIntegerField('Открыто', default=0)
    clicked_count = models.PositiveIntegerField('Кликов', default=0)
    bounced_count = models.PositiveIntegerField('Возвратов', default=0)
    
    # Метаданные
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена', auto_now=True)
    
    class Meta:
        verbose_name = 'Рассылка'
        verbose_name_plural = 'Рассылки'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.subject
