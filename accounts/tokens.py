"""
Токены для активации аккаунтов и верификации email
"""

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import six


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    """
    Генератор токенов для активации аккаунта
    """
    def _make_hash_value(self, user, timestamp):
        """
        Создает хеш для токена активации
        """
        return (
            six.text_type(user.pk) + six.text_type(timestamp) +
            six.text_type(user.is_active)
        )


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Генератор токенов для верификации email
    """
    def _make_hash_value(self, user, timestamp):
        """
        Создает хеш для токена верификации email
        """
        return (
            six.text_type(user.pk) + six.text_type(timestamp) +
            six.text_type(user.email)
        )


class PasswordResetTokenGenerator(PasswordResetTokenGenerator):
    """
    Кастомный генератор токенов для сброса пароля
    """
    def _make_hash_value(self, user, timestamp):
        """
        Создает хеш для токена сброса пароля
        """
        return (
            six.text_type(user.pk) + six.text_type(timestamp) +
            six.text_type(user.last_login)
        )


# Создаем экземпляры генераторов токенов
account_activation_token = AccountActivationTokenGenerator()
email_verification_token = EmailVerificationTokenGenerator()
password_reset_token = PasswordResetTokenGenerator()