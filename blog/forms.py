"""
Формы для блога интернет-магазина
"""

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from .models import Article, Category, Tag, Comment, Newsletter, NewsletterSubscriber


class ArticleForm(forms.ModelForm):
    """
    Форма для создания и редактирования статей
    """
    tags = forms.CharField(
        required=False,
        help_text='Введите теги через запятую',
        widget=forms.TextInput(attrs={
            'placeholder': 'мобильный телефон, смартфон, гаджеты'
        })
    )
    
    class Meta:
        model = Article
        fields = [
            'title', 'subtitle', 'slug', 'category', 'excerpt', 'content',
            'featured_image', 'meta_title', 'meta_description', 'meta_keywords',
            'is_published', 'is_featured', 'is_important', 'published_at'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Заголовок статьи'
            }),
            'subtitle': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Подзаголовок (опционально)'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'url-идентификатор'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'excerpt': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Краткое описание статьи для анонса'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Полный текст статьи'
            }),
            'featured_image': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
            'meta_title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Meta заголовок (опционально)'
            }),
            'meta_description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Meta описание (опционально)'
            }),
            'meta_keywords': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Meta ключевые слова (опционально)'
            }),
            'published_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Делаем некоторые поля необязательными
        self.fields['subtitle'].required = False
        self.fields['slug'].required = False
        self.fields['featured_image'].required = False
        self.fields['meta_title'].required = False
        self.fields['meta_description'].required = False
        self.fields['meta_keywords'].required = False
        self.fields['published_at'].required = False
        
        # Если статья новая и не опубликована, скрываем поле published_at
        if not self.instance.pk or not self.instance.is_published:
            self.fields['published_at'].widget = forms.HiddenInput()
    
    def clean_title(self):
        """Валидация заголовка"""
        title = self.cleaned_data.get('title')
        if not title:
            raise ValidationError('Заголовок обязателен')
        if len(title) < 5:
            raise ValidationError('Заголовок должен содержать минимум 5 символов')
        return title
    
    def clean_excerpt(self):
        """Валидация анонса"""
        excerpt = self.cleaned_data.get('excerpt')
        if not excerpt:
            raise ValidationError('Анонс обязателен')
        if len(excerpt) < 50:
            raise ValidationError('Анонс должен содержать минимум 50 символов')
        if len(excerpt) > 500:
            raise ValidationError('Анонс не должен превышать 500 символов')
        return excerpt
    
    def clean_content(self):
        """Валидация контента"""
        content = self.cleaned_data.get('content')
        if not content:
            raise ValidationError('Содержимое статьи обязательно')
        if len(content) < 200:
            raise ValidationError('Содержимое статьи должно содержать минимум 200 символов')
        return content
    
    def save(self, commit=True):
        """Сохранение статьи с обработкой тегов"""
        article = super().save(commit=False)
        
        # Обрабатываем теги
        tags_text = self.cleaned_data.get('tags', '')
        if tags_text and commit:
            tag_names = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
            
            # Создаем или получаем теги
            article.tags.clear()  # Очищаем существующие теги
            for tag_name in tag_names:
                tag, created = Tag.objects.get_or_create(
                    slug=tag_name.lower().replace(' ', '-'),
                    defaults={'name': tag_name}
                )
                article.tags.add(tag)
        
        if commit:
            article.save()
            self.save_m2m()
        
        return article


class ArticleSearchForm(forms.Form):
    """
    Форма поиска статей
    """
    search_query = forms.CharField(
        max_length=200,
        required=False,
        label='Поисковый запрос',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Поиск по статьям...'
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        label='Категория',
        empty_label='Все категории',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        label='Дата от',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        label='Дата до',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    author = forms.CharField(
        max_length=100,
        required=False,
        label='Автор',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя автора'
        })
    )


class CommentForm(forms.ModelForm):
    """
    Форма для комментариев
    """
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Ваш комментарий...'
            })
        }

class NewsletterForm(forms.ModelForm):
    """
    Форма для создания рассылки
    """
    class Meta:
        model = Newsletter
        fields = ['email', 'name', 'status']

class NewsletterSubscriberForm(forms.ModelForm):
    """
    Форма для подписки на рассылку
    """
    class Meta:
        model = NewsletterSubscriber
        fields = ['email', 'name']

class ContactForm(forms.Form):
    """
    Форма обратной связи
    """
    name = forms.CharField(
        max_length=100,
        label='Имя',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ваше имя'
        })
    )
    
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'email@example.com'
        })
    )
    
    subject = forms.CharField(
        max_length=200,
        label='Тема',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Тема сообщения'
        })
    )
    
    message = forms.CharField(
        label='Сообщение',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Ваше сообщение...'
        })
    )
    
    def clean_message(self):
        """Валидация сообщения"""
        message = self.cleaned_data.get('message')
        if not message:
            raise ValidationError('Сообщение обязательно')
        if len(message) < 20:
            raise ValidationError('Сообщение должно содержать минимум 20 символов')
        return message


class ArticleModerationForm(forms.ModelForm):
    """
    Форма модерации статей
    """
    class Meta:
        model = Article
        fields = ['is_published', 'is_featured', 'is_important']
        widgets = {
            'is_published': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_important': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }


class CommentModerationForm(forms.ModelForm):
    """
    Форма модерации комментариев
    """
    class Meta:
        model = Comment
        fields = ['status', 'is_spam']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_spam': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }