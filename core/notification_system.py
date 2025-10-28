"""
Система уведомлений для PhoneShop
Отправка email и SMS уведомлений при изменении статуса заказа
"""

from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.html import strip_tags
from django.urls import reverse
from orders.models import Order
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class OrderNotificationService:
    """
    Сервис для отправки уведомлений о заказах
    """
    
    def __init__(self):
        self.email_backend = getattr(settings, 'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
    
    def send_order_status_notification(self, order, old_status, new_status, user=None):
        """
        Отправка уведомления об изменении статуса заказа
        """
        try:
            # Определяем тип уведомления
            notification_type = self._get_notification_type(old_status, new_status)
            
            # Подготавливаем контекст
            context = {
                'order': order,
                'old_status': old_status,
                'new_status': new_status,
                'notification_type': notification_type,
                'user': user or order.user,
                'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000',
            }
            
            # Отправляем email уведомление
            if self._should_send_email_notification(order.user):
                self._send_email_notification(context)
            
            # Отправляем SMS уведомление (если настроено)
            if self._should_send_sms_notification(order.user):
                self._send_sms_notification(order.user, context)
            
            # Логируем отправку
            logger.info(f"Уведомление отправлено для заказа {order.order_number}")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления для заказа {order.order_number}: {str(e)}")
    
    def _get_notification_type(self, old_status, new_status):
        """Определяет тип уведомления"""
        status_mapping = {
            ('pending', 'processing'): 'order_confirmed',
            ('pending', 'cancelled'): 'order_cancelled',
            ('processing', 'assembly'): 'order_assembly',
            ('assembly', 'shipped'): 'order_shipped',
            ('shipped', 'delivered'): 'order_delivered',
            ('delivered', 'completed'): 'order_completed',
        }
        
        key = (old_status, new_status)
        return status_mapping.get(key, 'order_status_changed')
    
    def _should_send_email_notification(self, user):
        """Проверяет, нужно ли отправлять email уведомление"""
        if not user.is_authenticated:
            return False
        
        # Проверяем настройки пользователя
        try:
            profile = user.profile
            return profile.email_notifications
        except:
            return True  # По умолчанию отправляем
    
    def _should_send_sms_notification(self, user):
        """Проверяет, нужно ли отправлять SMS уведомление"""
        if not user.is_authenticated or not user.phone:
            return False
        
        try:
            profile = user.profile
            return profile.sms_notifications
        except:
            return False
    
    def _send_email_notification(self, context):
        """Отправка email уведомления"""
        try:
            user = context['user']
            notification_type = context['notification_type']
            order = context['order']
            
            # Определяем тему и шаблон
            email_config = self._get_email_config(notification_type)
            
            # Подготавливаем контекст для шаблона
            email_context = {
                **context,
                'order_url': f"{context['site_url']}/orders/{order.order_number}/",
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@phoneshop.ru'),
            }
            
            # Рендерим HTML и текстовую версию
            html_message = render_to_string(email_config['template_html'], email_context)
            text_message = render_to_string(email_config['template_text'], email_context)
            text_message = strip_tags(html_message)  # Fallback если текстового шаблона нет
            
            # Создаем email
            email = EmailMultiAlternatives(
                subject=email_config['subject'],
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@phoneshop.ru',
                to=[user.email],
            )
            email.attach_alternative(html_message, "text/html")
            
            # Отправляем
            email.send()
            
        except Exception as e:
            logger.error(f"Ошибка при отправке email: {str(e)}")
    
    def _send_sms_notification(self, user, context):
        """Отправка SMS уведомления (заглушка)"""
        # Здесь можно интегрировать с SMS провайдером (например, Twilio, SMS.ru)
        logger.info(f"SMS уведомление для {user.phone}: заказ {context['order'].order_number}")
        # TODO: Реализовать отправку SMS
    
    def _get_email_config(self, notification_type):
        """Получает конфигурацию email для типа уведомления"""
        configs = {
            'order_confirmed': {
                'subject': 'Заказ подтвержден - PhoneShop',
                'template_html': 'emails/order_confirmed.html',
                'template_text': 'emails/order_confirmed.txt',
            },
            'order_cancelled': {
                'subject': 'Заказ отменен - PhoneShop',
                'template_html': 'emails/order_cancelled.html',
                'template_text': 'emails/order_cancelled.txt',
            },
            'order_assembly': {
                'subject': 'Заказ взят в сборку - PhoneShop',
                'template_html': 'emails/order_assembly.html',
                'template_text': 'emails/order_assembly.txt',
            },
            'order_shipped': {
                'subject': 'Заказ отправлен - PhoneShop',
                'template_html': 'emails/order_shipped.html',
                'template_text': 'emails/order_shipped.txt',
            },
            'order_delivered': {
                'subject': 'Заказ доставлен - PhoneShop',
                'template_html': 'emails/order_delivered.html',
                'template_text': 'emails/order_delivered.txt',
            },
            'order_completed': {
                'subject': 'Заказ выполнен - PhoneShop',
                'template_html': 'emails/order_completed.html',
                'template_text': 'emails/order_completed.txt',
            },
        }
        
        return configs.get(notification_type, configs['order_confirmed'])
    
    def send_welcome_email(self, user):
        """
        Отправка приветственного email при регистрации
        """
        try:
            context = {
                'user': user,
                'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000',
                'login_url': f"{context['site_url']}/accounts/login/",
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@phoneshop.ru'),
            }
            
            html_message = render_to_string('emails/welcome.html', context)
            text_message = render_to_string('emails/welcome.txt', context)
            text_message = strip_tags(html_message)
            
            email = EmailMultiAlternatives(
                subject='Добро пожаловать в PhoneShop!',
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@phoneshop.ru',
                to=[user.email],
            )
            email.attach_alternative(html_message, "text/html")
            email.send()
            
        except Exception as e:
            logger.error(f"Ошибка при отправке приветственного email: {str(e)}")
    
    def send_password_reset_email(self, user, reset_url):
        """
        Отправка email для сброса пароля
        """
        try:
            context = {
                'user': user,
                'reset_url': reset_url,
                'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000',
            }
            
            html_message = render_to_string('emails/password_reset.html', context)
            text_message = render_to_string('emails/password_reset.txt', context)
            text_message = strip_tags(html_message)
            
            email = EmailMultiAlternatives(
                subject='Восстановление пароля - PhoneShop',
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@phoneshop.ru',
                to=[user.email],
            )
            email.attach_alternative(html_message, "text/html")
            email.send()
            
        except Exception as e:
            logger.error(f"Ошибка при отправке email восстановления пароля: {str(e)}")


# Глобальный экземпляр сервиса
notification_service = OrderNotificationService()


# Функции для использования в других частях приложения
def notify_order_status_change(order, old_status, new_status, user=None):
    """
    Удобная функция для отправки уведомления об изменении статуса заказа
    """
    notification_service.send_order_status_notification(order, old_status, new_status, user)


def send_welcome_email(user):
    """Удобная функция для отправки приветственного email"""
    notification_service.send_welcome_email(user)


def send_password_reset_email(user, reset_url):
    """Удобная функция для отправки email восстановления пароля"""
    notification_service.send_password_reset_email(user, reset_url)