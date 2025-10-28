"""
Формы для системы отзывов и рейтингов
"""

from django import forms
from django.core.validators import FileExtensionValidator, MaxLengthValidator
from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions
from datetime import date
from .models import Review, ReviewPhoto, ReviewVideo, ReviewHelpfulness, ReviewFlag


class ReviewForm(forms.ModelForm):
    """
    Форма для создания и редактирования отзывов
    """
    RATING_CHOICES = [
        (1, '1 - Очень плохо'),
        (2, '2 - Плохо'),
        (3, '3 - Удовлетворительно'),
        (4, '4 - Хорошо'),
        (5, '5 - Отлично'),
    ]
    
    rating = forms.ChoiceField(
        label='Оценка',
        choices=RATING_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'rating-input'
        })
    )
    
    title = forms.CharField(
        label='Заголовок отзыва',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Кратко опишите ваше мнение'
        })
    )
    
    text = forms.CharField(
        label='Текст отзыва',
        max_length=2000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Поделитесь подробным мнением о товаре...'
        })
    )
    
    pros = forms.CharField(
        label='Достоинства',
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Что вам понравилось в товаре?'
        })
    )
    
    cons = forms.CharField(
        label='Недостатки',
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Что вам не понравилось в товаре?'
        })
    )
    
    recommend = forms.BooleanField(
        label='Рекомендую товар',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    photos = forms.FileField(
        label='Фотографии',
        required=False,
        help_text='Максимум 5 фото, размер не более 5 МБ каждое',
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'multiple': True,
            'accept': 'image/*'
        })
    )
    
    videos = forms.FileField(
        label='Видео',
        required=False,
        help_text='Максимум 2 видео, размер не более 50 МБ каждое',
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'multiple': True,
            'accept': 'video/*'
        })
    )
    
    class Meta:
        model = Review
        fields = ('rating', 'title', 'text', 'pros', 'cons', 'recommend')
    
    def __init__(self, *args, **kwargs):
        product = kwargs.pop('product', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.product = product
        self.user = user
    
    def clean_photos(self):
        """Валидация загружаемых фотографий"""
        photos = self.cleaned_data.get('photos', [])
        
        if not photos:
            return photos
        
        if len(photos) > 5:
            raise ValidationError('Можно загрузить максимум 5 фотографий')
        
        for photo in photos:
            # Проверяем размер файла (5 МБ)
            if photo.size > 5 * 1024 * 1024:
                raise ValidationError(f'Файл {photo.name} слишком большой. Максимальный размер 5 МБ.')
            
            # Проверяем формат
            if not photo.content_type.startswith('image/'):
                raise ValidationError(f'Файл {photo.name} не является изображением')
            
            # Проверяем размеры изображения
            try:
                width, height = get_image_dimensions(photo)
                if width > 3000 or height > 3000:
                    raise ValidationError(f'Размер изображения {photo.name} слишком большой. Максимум 3000x3000 пикселей.')
            except AttributeError:
                raise ValidationError(f'Невозможно определить размеры изображения {photo.name}')
        
        return photos
    
    def clean_videos(self):
        """Валидация загружаемых видео"""
        videos = self.cleaned_data.get('videos', [])
        
        if not videos:
            return videos
        
        if len(videos) > 2:
            raise ValidationError('Можно загрузить максимум 2 видео')
        
        for video in videos:
            # Проверяем размер файла (50 МБ)
            if video.size > 50 * 1024 * 1024:
                raise ValidationError(f'Видео {video.name} слишком большое. Максимальный размер 50 МБ.')
            
            # Проверяем формат
            allowed_formats = ['video/mp4', 'video/avi', 'video/mov', 'video/wmv', 'video/quicktime']
            if video.content_type not in allowed_formats:
                raise ValidationError(f'Формат видео {video.name} не поддерживается. Разрешены: MP4, AVI, MOV, WMV.')
        
        return videos
    
    def clean_text(self):
        """Валидация текста отзыва"""
        text = self.cleaned_data.get('text', '')
        
        if len(text) < 50:
            raise ValidationError('Текст отзыва должен содержать минимум 50 символов')
        
        # Проверяем на спам (простые проверки)
        if text.count('http') > 3:
            raise ValidationError('Слишком много ссылок в тексте отзыва')
        
        # Проверяем на повторяющиеся символы
        if '!!!!' in text or '????' in text:
            raise ValidationError('Используйте не более 2 знаков восклицания или вопроса подряд')
        
        return text
    
    def save(self, commit=True):
        """Сохранение отзыва с медиафайлами"""
        review = super().save(commit=False)
        
        if commit:
            review.save()
            
            # Сохраняем фотографии
            photos = self.cleaned_data.get('photos', [])
            for photo in photos:
                ReviewPhoto.objects.create(review=review, image=photo)
            
            # Сохраняем видео
            videos = self.cleaned_data.get('videos', [])
            for video in videos:
                ReviewVideo.objects.create(review=review, video=video)
            
            # Обновляем статус подтверждения покупки
            if hasattr(self.user, 'has_verified_purchase'):
                review.is_verified_purchase = True
            
            review.save()
        
        return review


class ReviewHelpfulnessForm(forms.Form):
    """
    Форма для голосования за полезность отзыва
    """
    is_helpful = forms.BooleanField(
        required=False,
        widget=forms.HiddenInput()
    )


class ReviewFlagForm(forms.ModelForm):
    """
    Форма для подачи жалобы на отзыв
    """
    FLAG_REASONS = [
        ('spam', 'Спам или реклама'),
        ('offensive', 'Оскорбительное содержание'),
        ('fake', 'Фейковый отзыв'),
        ('irrelevant', 'Не относится к товару'),
        ('copyright', 'Нарушение авторских прав'),
        ('other', 'Другое'),
    ]
    
    reason = forms.ChoiceField(
        label='Причина жалобы',
        choices=FLAG_REASONS,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    reason_text = forms.CharField(
        label='Подробное описание',
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Дополнительные детали о нарушении...'
        })
    )
    
    class Meta:
        model = ReviewFlag
        fields = ('reason', 'reason_text')


class ReviewFilterForm(forms.Form):
    """
    Форма фильтрации отзывов
    """
    RATING_CHOICES = [
        ('', 'Все рейтинги'),
        (5, '5 звёзд'),
        (4, '4 звезды'),
        (3, '3 звезды'),
        (2, '2 звезды'),
        (1, '1 звезда'),
    ]
    
    SORT_CHOICES = [
        ('', 'Сортировка'),
        ('-created_at', 'По дате (новые первыми)'),
        ('created_at', 'По дате (старые первыми)'),
        ('-helpful_count', 'По полезности'),
        ('-rating', 'По рейтингу (высокий)'),
        ('rating', 'По рейтингу (низкий)'),
    ]
    
    rating = forms.ChoiceField(
        label='Рейтинг',
        choices=RATING_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    has_photos = forms.BooleanField(
        label='Только с фото',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    has_videos = forms.BooleanField(
        label='Только с видео',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    verified_only = forms.BooleanField(
        label='Только проверенные покупки',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    sort_by = forms.ChoiceField(
        label='Сортировка',
        choices=SORT_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )


class ReviewSearchForm(forms.Form):
    """
    Форма поиска отзывов (для администраторов)
    """
    search_query = forms.CharField(
        label='Поиск по тексту',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Поиск в заголовке, тексте, достоинствах, недостатках...'
        })
    )
    
    product_name = forms.CharField(
        label='Название товара',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Фильтр по товару...'
        })
    )
    
    user_name = forms.CharField(
        label='Имя пользователя',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Фильтр по пользователю...'
        })
    )
    
    rating = forms.ChoiceField(
        label='Рейтинг',
        required=False,
        choices=[('', 'Все рейтинги')] + [(i, f'{i} звёзд') for i in range(1, 6)],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    STATUS_CHOICES = [
        ('', 'Все статусы'),
        ('approved', 'Одобренные'),
        ('pending', 'На модерации'),
        ('rejected', 'Отклоненные'),
    ]
    
    status = forms.ChoiceField(
        label='Статус модерации',
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    date_from = forms.DateField(
        label='Дата создания с',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        label='Дата создания по',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    has_photos = forms.BooleanField(
        label='С фотографиями',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    verified_only = forms.BooleanField(
        label='Только проверенные покупки',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )


class ReviewModerationForm(forms.Form):
    """
    Форма модерации отзывов (для администраторов)
    """
    ACTION_CHOICES = [
        ('approve', 'Одобрить'),
        ('reject', 'Отклонить'),
        ('edit', 'Редактировать'),
        ('delete', 'Удалить'),
    ]
    
    action = forms.ChoiceField(
        label='Действие',
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    admin_note = forms.CharField(
        label='Комментарий модератора',
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Комментарий для автора отзыва или внутренняя заметка...'
        })
    )
    
    notify_author = forms.BooleanField(
        label='Уведомить автора',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )


class BulkReviewActionForm(forms.Form):
    """
    Форма массовых действий с отзывами
    """
    ACTION_CHOICES = [
        ('approve', 'Одобрить'),
        ('reject', 'Отклонить'),
        ('delete', 'Удалить'),
        ('export', 'Экспорт в Excel'),
        ('moderate', 'Отправить на модерацию'),
    ]
    
    action = forms.ChoiceField(
        label='Действие',
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    review_ids = forms.CharField(
        label='ID отзывов',
        widget=forms.HiddenInput(),
        help_text='JSON массив ID отзывов'
    )
    
    reason = forms.CharField(
        label='Причина (для отклонения)',
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Причина массового действия...'
        })
    )


class ReviewStatsForm(forms.Form):
    """
    Форма для просмотра статистики отзывов
    """
    PERIOD_CHOICES = [
        ('week', 'Последняя неделя'),
        ('month', 'Последний месяц'),
        ('quarter', 'Последний квартал'),
        ('year', 'Последний год'),
        ('all', 'Все время'),
    ]
    
    period = forms.ChoiceField(
        label='Период анализа',
        choices=PERIOD_CHOICES,
        initial='month',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    group_by = forms.ChoiceField(
        label='Группировка',
        choices=[
            ('day', 'По дням'),
            ('week', 'По неделям'),
            ('month', 'По месяцам'),
        ],
        initial='month',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    category_filter = forms.CharField(
        label='Фильтр по категории',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Название категории для анализа...'
        })
    )
    
    min_rating = forms.ChoiceField(
        label='Минимальный рейтинг',
        required=False,
        choices=[(i, f'Минимум {i} звёзд') for i in range(1, 6)],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )


class ReviewReplyForm(forms.ModelForm):
    """
    Форма ответа на отзыв (для администраторов)
    """
    class Meta:
        model = Review
        fields = ('admin_reply',)
        widgets = {
            'admin_reply': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Ответ на отзыв пользователя...'
            })
        }
    
    def clean_admin_reply(self):
        reply = self.cleaned_data.get('admin_reply', '')
        if reply and len(reply) > 1000:
            raise ValidationError('Ответ не должен превышать 1000 символов')
        return reply


class ReviewAnalyticsForm(forms.Form):
    """
    Форма для аналитики отзывов
    """
    METRIC_CHOICES = [
        ('count', 'Количество отзывов'),
        ('avg_rating', 'Средний рейтинг'),
        ('approval_rate', 'Процент одобрения'),
        ('photos_rate', 'Процент с фото'),
        ('verified_rate', 'Процент проверенных'),
        ('helpfulness', 'Средняя полезность'),
    ]
    
    metric = forms.ChoiceField(
        label='Метрика',
        choices=METRIC_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    comparison_period = forms.BooleanField(
        label='Сравнить с предыдущим периодом',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    export_format = forms.ChoiceField(
        label='Формат экспорта',
        choices=[
            ('pdf', 'PDF отчет'),
            ('excel', 'Excel таблица'),
            ('csv', 'CSV файл'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )


class ReviewTagForm(forms.Form):
    """
    Форма для тегирования отзывов
    """
    TAGS_CHOICES = [
        ('helpful', 'Полезный'),
        ('detailed', 'Подробный'),
        ('short', 'Краткий'),
        ('with_photos', 'С фото'),
        ('with_videos', 'С видео'),
        ('verified', 'Проверенный'),
        ('negative', 'Негативный'),
        ('positive', 'Позитивный'),
        ('spam', 'Спам'),
        ('inappropriate', 'Неуместный'),
    ]
    
    tag = forms.ChoiceField(
        label='Тег',
        choices=TAGS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    action = forms.ChoiceField(
        label='Действие',
        choices=[
            ('add', 'Добавить тег'),
            ('remove', 'Удалить тег'),
        ],
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )


class ReviewNotificationForm(forms.Form):
    """
    Форма настройки уведомлений о новых отзывах
    """
    notify_new_reviews = forms.BooleanField(
        label='Уведомлять о новых отзывах',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    notify_negative_reviews = forms.BooleanField(
        label='Уведомлять о негативных отзывах',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    email_recipients = forms.CharField(
        label='Email адреса получателей',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'email1@example.com, email2@example.com'
        })
    )
    
    review_threshold = forms.ChoiceField(
        label='Порог для уведомления',
        choices=[
            (1, 'Все новые отзывы'),
            (3, 'При 3+ отзывах'),
            (5, 'При 5+ отзывах'),
            (10, 'При 10+ отзывах'),
        ],
        initial=1,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )