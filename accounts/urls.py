"""
URL маршруты для приложения accounts (аутентификация и пользователи)
"""

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    # Логин и выход (переопределенные с кастомными шаблонами)
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Сброс пароля с кастомными шаблонами
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset_form.html'
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # Смена пароля (для авторизованных пользователей)
    path('password-change/', auth_views.PasswordChangeView.as_view(
        template_name='accounts/password_change_form.html'
    ), name='password_change'),
    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='accounts/password_change_done.html'
    ), name='password_change_done'),
    
    # Регистрация
    path('register/', views.register, name='register'),
    path('register/complete/', views.registration_complete, name='registration_complete'),
    
    # Подтверждение email
    path('email-verify/<str:token>/', views.verify_email, name='verify_email'),
    path('email-verification-sent/', views.email_verification_sent, name='email_verification_sent'),
    path('resend-email-verification/', views.resend_email_verification, name='resend_email_verification'),
    
    # Активация аккаунта
    path('activate/<str:uidb64>/<str:token>/', views.activate_account, name='activate_account'),
    path('activation-sent/', views.activation_sent, name='activation_sent'),
    
    # Профиль пользователя
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/settings/', views.profile_settings, name='profile_settings'),
    path('profile/update/', views.profile_update, name='profile_update'),
    
    # Управление адресами
    path('addresses/', views.addresses_list, name='addresses_list'),
    path('addresses/add/', views.address_create, name='address_create'),
    path('addresses/<int:address_id>/edit/', views.address_update, name='address_update'),
    path('addresses/<int:address_id>/delete/', views.address_delete, name='address_delete'),
    path('addresses/<int:address_id>/set-default/', views.address_set_default, name='address_set_default'),
    
    # Избранное и сравнение
    path('wishlist/', views.wishlist, name='wishlist'),
    path('compare/', views.compare_list, name='compare_list'),
    path('ajax/add-to-wishlist/', views.add_to_wishlist, name='add_to_wishlist'),
    path('ajax/remove-from-wishlist/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('ajax/add-to-compare/', views.add_to_compare, name='add_to_compare'),
    path('ajax/remove-from-compare/', views.remove_from_compare, name='remove_from_compare'),
    
    # Настройки аккаунта
    path('settings/change-password/', views.change_password, name='change_password'),
    path('settings/notifications/', views.notification_settings, name='notification_settings'),
    path('settings/account/', views.account_settings, name='account_settings'),
    path('settings/delete/', views.delete_account, name='delete_account'),
    
    # История заказов
    path('orders/', views.order_history, name='order_history'),
    
    # Бонусная система
    path('bonuses/', views.bonuses, name='bonuses'),
    path('loyalty/', views.loyalty_program, name='loyalty_program'),
    
    # Аналитика
    path('analytics/', views.analytics, name='analytics'),
    
    # Скачивание данных
    path('download-data/', views.download_data, name='download_data'),
    
    # Поддержка
    path('support/', views.support, name='support'),
    
    # AJAX endpoints
    path('ajax/check-username/', views.check_username_availability, name='check_username_availability'),
    path('ajax/check-email/', views.check_email_availability, name='check_email_availability'),
    path('ajax/check-phone/', views.check_phone_availability, name='check_phone_availability'),
    path('ajax/update-profile/', views.update_profile_ajax, name='update_profile_ajax'),
    path('ajax/user-stats/', views.get_user_stats_ajax, name='get_user_stats_ajax'),
    path('ajax/notification-preferences/', views.update_notification_preference, name='update_notification_preference'),
    
    # API endpoints для мобильного приложения
    path('api/register/', views.api_register, name='api_register'),
    path('api/login/', views.api_login, name='api_login'),
    path('api/logout/', views.api_logout, name='api_logout'),
    path('api/profile/', views.api_profile, name='api_profile'),
    path('api/change-password/', views.api_change_password, name='api_change_password'),
    path('api/forgot-password/', views.api_forgot_password, name='api_forgot_password'),
    path('api/reset-password/<str:token>/', views.api_reset_password, name='api_reset_password'),
    
    # Дополнительные страницы
    path('age-verification/', views.age_verification, name='age_verification'),
    path('age-verification/confirm/', views.confirm_age_verification, name='confirm_age_verification'),
    
    # Безопасность
    path('security/', views.security_settings, name='security_settings'),
    path('sessions/', views.active_sessions, name='active_sessions'),
    path('sessions/<int:session_id>/terminate/', views.terminate_session, name='terminate_session'),
    
    # История активности
    path('activity/', views.activity_log, name='activity_log'),
    path('activity/data/', views.activity_log_data, name='activity_log_data'),
    
    # Уведомления
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    
    # Дополнительные функции
    path('bonus/dashboard/', views.bonus_dashboard, name='bonus_dashboard'),
    path('bonus/history/', views.bonus_history, name='bonus_history'),
    path('bonus/referral/', views.referral_program, name='referral_program'),
    path('bonus/referral/code/', views.get_referral_code, name='get_referral_code'),
    path('bonus/partner/', views.partner_program, name='partner_program'),
]