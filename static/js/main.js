/**
 * PhoneShop - Основной JavaScript файл для интернет-магазина
 * Включает функциональность корзины, AJAX-запросы, анимации и общую интерактивность
 */

(function($) {
    'use strict';

    // Глобальные переменные
    const CSRF_TOKEN = $('meta[name="csrf-token"]').attr('content');
    const CART_COUNT_URL = '{% url "cart:get_cart_count" %}';
    const ADD_TO_CART_URL = '{% url "cart:add_to_cart" %}';
    const UPDATE_CART_URL = '{% url "cart:update_item_quantity" %}';
    const REMOVE_FROM_CART_URL = '{% url "cart:remove_item" %}';
    const WISHLIST_URL = '{% url "accounts:add_to_wishlist" %}';
    const COMPARE_URL = '{% url "accounts:add_to_compare" %}';

    // Инициализация при загрузке страницы
    $(document).ready(function() {
        initializeComponents();
        initializeEventHandlers();
        updateCartCount();
    });

    /**
     * Инициализация компонентов
     */
    function initializeComponents() {
        // Инициализация tooltips
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });

        // Инициализация popovers
        var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        var popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });

        // Анимация элементов при загрузке
        $('.fade-in').addClass('animated');

        // Smooth scrolling для якорных ссылок
        $('a[href^="#"]').click(function(e) {
            e.preventDefault();
            const target = $(this.getAttribute('href'));
            if (target.length) {
                $('html, body').animate({
                    scrollTop: target.offset().top - 100
                }, 500);
            }
        });
    }

    /**
     * Инициализация обработчиков событий
     */
    function initializeEventHandlers() {
        // AJAX обработчик для кнопок "В корзину"
        $(document).on('click', '.add-to-cart, .quick-add-to-cart', handleAddToCart);
        
        // Обработчик для кнопок "Быстрый просмотр"
        $(document).on('click', '.quick-view', handleQuickView);
        
        // Обработчик для кнопок "В избранное"
        $(document).on('click', '.add-to-wishlist', handleAddToWishlist);
        
        // Обработчик для кнопок "В сравнение"
        $(document).on('click', '.add-to-compare', handleAddToCompare);
        
        // Обработчик для изменения количества в корзине
        $(document).on('click', '.quantity-btn', handleQuantityChange);
        
        // Обработчик для изменения количества через input
        $(document).on('change', '.quantity-input', handleQuantityInputChange);
        
        // Обработчик для поиска с автодополнением
        $('#search-input').on('input', debounce(handleSearchInput, 300));
        
        // Обработчик для фильтров
        $('.filter-form').on('change', 'input, select', handleFilterChange);
        
        // Обработчик для сортировки
        $('#sort-select').on('change', handleSortChange);
        
        // Обработчики для форм
        $('.ajax-form').on('submit', handleAjaxFormSubmit);
        
        // Обработчик для модальных окон
        $(document).on('shown.bs.modal', '.modal', function() {
            $(this).find('input:first').focus();
        });
        
        // Обработчик для закрытия уведомлений
        $(document).on('click', '.close-notification', closeNotification);
        
        // Lazy loading для изображений
        if ('IntersectionObserver' in window) {
            initializeLazyLoading();
        }
    }

    /**
     * Добавление товара в корзину
     */
    function handleAddToCart(e) {
        e.preventDefault();
        
        const button = $(this);
        const productId = button.data('product-id') || button.closest('[data-product-id]').data('product-id');
        const quantity = button.data('quantity') || 1;
        const originalText = button.html();
        
        // Блокируем кнопку и показываем загрузку
        button.prop('disabled', true).addClass('loading');
        showSpinner(button);
        
        // AJAX запрос
        $.ajax({
            url: ADD_TO_CART_URL,
            method: 'POST',
            data: {
                product_id: productId,
                quantity: quantity,
                csrfmiddlewaretoken: CSRF_TOKEN
            },
            success: function(response) {
                if (response.success) {
                    // Успешное добавление
                    showNotification('Товар добавлен в корзину', 'success');
                    updateCartCount();
                    
                    // Анимация кнопки
                    button.removeClass('btn-primary').addClass('btn-success');
                    button.html('<i class="fas fa-check"></i> Добавлено');
                    
                    setTimeout(function() {
                        button.removeClass('btn-success').addClass('btn-primary');
                        button.html(originalText);
                    }, 2000);
                } else {
                    // Ошибка
                    showNotification(response.message || 'Ошибка при добавлении товара', 'error');
                    button.removeClass('loading').prop('disabled', false);
                    button.html(originalText);
                }
            },
            error: function() {
                showNotification('Произошла ошибка при добавлении товара', 'error');
                button.removeClass('loading').prop('disabled', false);
                button.html(originalText);
            }
        });
    }

    /**
     * Быстрый просмотр товара
     */
    function handleQuickView(e) {
        e.preventDefault();
        
        const button = $(this);
        const productId = button.data('product-id');
        
        // Показываем модальное окно с прелоадером
        $('#quickViewModal .modal-body').html('<div class="text-center"><div class="spinner"></div><p>Загрузка...</p></div>');
        $('#quickViewModal').modal('show');
        
        // Загружаем данные товара
        $.ajax({
            url: `/catalog/quick-view/${productId}/`,
            method: 'GET',
            success: function(response) {
                $('#quickViewModal .modal-body').html(response);
            },
            error: function() {
                $('#quickViewModal .modal-body').html('<div class="text-center text-danger">Ошибка загрузки товара</div>');
            }
        });
    }

    /**
     * Добавление в избранное
     */
    function handleAddToWishlist(e) {
        e.preventDefault();
        
        const button = $(this);
        const productId = button.data('product-id');
        
        $.ajax({
            url: WISHLIST_URL,
            method: 'POST',
            data: {
                product_id: productId,
                csrfmiddlewaretoken: CSRF_TOKEN
            },
            success: function(response) {
                if (response.status === 'added') {
                    button.removeClass('btn-outline-danger').addClass('btn-danger');
                    button.html('<i class="fas fa-heart"></i>');
                    showNotification('Товар добавлен в избранное', 'success');
                } else if (response.status === 'removed') {
                    button.removeClass('btn-danger').addClass('btn-outline-danger');
                    button.html('<i class="far fa-heart"></i>');
                    showNotification('Товар удален из избранного', 'info');
                }
            },
            error: function() {
                showNotification('Ошибка при работе с избранным', 'error');
            }
        });
    }

    /**
     * Добавление в сравнение
     */
    function handleAddToCompare(e) {
        e.preventDefault();
        
        const button = $(this);
        const productId = button.data('product-id');
        
        $.ajax({
            url: COMPARE_URL,
            method: 'POST',
            data: {
                product_id: productId,
                csrfmiddlewaretoken: CSRF_TOKEN
            },
            success: function(response) {
                if (response.status === 'added') {
                    button.removeClass('btn-outline-info').addClass('btn-info');
                    showNotification('Товар добавлен в сравнение', 'success');
                } else if (response.status === 'removed') {
                    button.removeClass('btn-info').addClass('btn-outline-info');
                    showNotification('Товар удален из сравнения', 'info');
                } else if (response.error) {
                    showNotification(response.error, 'warning');
                }
            },
            error: function() {
                showNotification('Ошибка при работе с сравнением', 'error');
            }
        });
    }

    /**
     * Изменение количества товара
     */
    function handleQuantityChange(e) {
        e.preventDefault();
        
        const button = $(this);
        const cartItem = button.closest('.cart-item, .product-card');
        const itemId = cartItem.data('item-id') || cartItem.data('product-id');
        const isIncrease = button.hasClass('increase-btn');
        const currentQuantity = parseInt(button.data('current-qty')) || 1;
        const newQuantity = isIncrease ? currentQuantity + 1 : currentQuantity - 1;
        
        if (newQuantity < 1) {
            removeFromCart(itemId);
            return;
        }
        
        updateCartItemQuantity(itemId, newQuantity);
    }

    /**
     * Изменение количества через input
     */
    function handleQuantityInputChange(e) {
        const input = $(this);
        const cartItem = input.closest('.cart-item, .product-card');
        const itemId = cartItem.data('item-id') || cartItem.data('product-id');
        const newQuantity = parseInt(input.val());
        
        if (newQuantity < 1) {
            removeFromCart(itemId);
            return;
        }
        
        updateCartItemQuantity(itemId, newQuantity);
    }

    /**
     * Обновление количества товара в корзине
     */
    function updateCartItemQuantity(itemId, quantity) {
        $.ajax({
            url: UPDATE_CART_URL,
            method: 'POST',
            data: {
                item_id: itemId,
                quantity: quantity,
                csrfmiddlewaretoken: CSRF_TOKEN
            },
            success: function(response) {
                if (response.success) {
                    location.reload(); // Перезагружаем страницу для обновления суммы
                } else {
                    showNotification(response.message || 'Ошибка при обновлении количества', 'error');
                }
            },
            error: function() {
                showNotification('Произошла ошибка при обновлении количества', 'error');
            }
        });
    }

    /**
     * Удаление товара из корзины
     */
    function removeFromCart(itemId) {
        if (confirm('Удалить товар из корзины?')) {
            $.ajax({
                url: REMOVE_FROM_CART_URL,
                method: 'POST',
                data: {
                    item_id: itemId,
                    csrfmiddlewaretoken: CSRF_TOKEN
                },
                success: function(response) {
                    if (response.success) {
                        location.reload();
                    } else {
                        showNotification(response.message || 'Ошибка при удалении товара', 'error');
                    }
                },
                error: function() {
                    showNotification('Произошла ошибка при удалении товара', 'error');
                }
            });
        }
    }

    /**
     * Поиск с автодополнением
     */
    function handleSearchInput(e) {
        const query = $(this).val();
        
        if (query.length < 2) {
            $('.search-suggestions').hide();
            return;
        }
        
        $.ajax({
            url: '/catalog/search/suggestions/',
            method: 'GET',
            data: { q: query },
            success: function(response) {
                displaySearchSuggestions(response);
            }
        });
    }

    /**
     * Отображение поисковых подсказок
     */
    function displaySearchSuggestions(data) {
        const container = $('.search-suggestions');
        let html = '';
        
        if (data.products && data.products.length > 0) {
            html += '<div class="suggestion-group"><h6>Товары</h6>';
            data.products.forEach(function(product) {
                html += `<div class="suggestion-item" data-url="/catalog/product/${product.slug}/">${product.name}</div>`;
            });
            html += '</div>';
        }
        
        if (data.brands && data.brands.length > 0) {
            html += '<div class="suggestion-group"><h6>Бренды</h6>';
            data.brands.forEach(function(brand) {
                html += `<div class="suggestion-item" data-url="/catalog/brand/${brand.slug}/">${brand.name}</div>`;
            });
            html += '</div>';
        }
        
        if (html) {
            container.html(html).show();
        } else {
            container.hide();
        }
    }

    /**
     * Обработка изменений фильтров
     */
    function handleFilterChange(e) {
        const form = $(this).closest('.filter-form');
        const url = new URL(window.location);
        
        // Обновляем параметры URL
        form.find('input, select').each(function() {
            const field = $(this);
            const name = field.attr('name');
            const value = field.val();
            
            if (value) {
                url.searchParams.set(name, value);
            } else {
                url.searchParams.delete(name);
            }
        });
        
        // Переходим на новый URL
        window.location.href = url.toString();
    }

    /**
     * Обработка сортировки
     */
    function handleSortChange(e) {
        const sortValue = $(this).val();
        const url = new URL(window.location);
        url.searchParams.set('sort', sortValue);
        window.location.href = url.toString();
    }

    /**
     * AJAX отправка форм
     */
    function handleAjaxFormSubmit(e) {
        e.preventDefault();
        
        const form = $(this);
        const url = form.attr('action') || window.location.href;
        const method = form.attr('method') || 'POST';
        const data = form.serialize();
        
        const submitButton = form.find('[type="submit"]');
        const originalText = submitButton.html();
        
        submitButton.prop('disabled', true).html('<div class="spinner"></div> Обработка...');
        
        $.ajax({
            url: url,
            method: method,
            data: data,
            success: function(response) {
                if (response.success) {
                    showNotification(response.message || 'Успешно выполнено', 'success');
                    if (response.redirect) {
                        setTimeout(function() {
                            window.location.href = response.redirect;
                        }, 1000);
                    }
                } else {
                    showNotification(response.message || 'Произошла ошибка', 'error');
                    if (response.errors) {
                        displayFormErrors(form, response.errors);
                    }
                }
            },
            error: function() {
                showNotification('Произошла ошибка при отправке формы', 'error');
            },
            complete: function() {
                submitButton.prop('disabled', false).html(originalText);
            }
        });
    }

    /**
     * Обновление счетчика корзины
     */
    function updateCartCount() {
        $.ajax({
            url: CART_COUNT_URL,
            method: 'GET',
            success: function(data) {
                $('#cart-count').text(data.count || 0);
                $('.cart-count-badge').text(data.count || 0);
            },
            error: function() {
                console.log('Не удалось обновить счетчик корзины');
            }
        });
    }

    /**
     * Показ уведомлений
     */
    function showNotification(message, type) {
        const notification = $(`
            <div class="alert alert-${type} alert-dismissible fade show notification" role="alert">
                ${message}
                <button type="button" class="btn-close close-notification"></button>
            </div>
        `);
        
        $('body').append(notification);
        
        // Автоматическое скрытие через 5 секунд
        setTimeout(function() {
            notification.fadeOut(function() {
                $(this).remove();
            });
        }, 5000);
    }

    /**
     * Закрытие уведомления
     */
    function closeNotification(e) {
        e.preventDefault();
        $(this).closest('.alert').fadeOut(function() {
            $(this).remove();
        });
    }

    /**
     * Показ спиннера
     */
    function showSpinner(element) {
        element.html('<div class="spinner"></div>');
    }

    /**
     * Отображение ошибок формы
     */
    function displayFormErrors(form, errors) {
        form.find('.is-invalid').removeClass('is-invalid');
        form.find('.invalid-feedback').remove();
        
        Object.keys(errors).forEach(function(field) {
            const fieldElement = form.find(`[name="${field}"]`);
            fieldElement.addClass('is-invalid');
            fieldElement.after(`<div class="invalid-feedback">${errors[field][0]}</div>`);
        });
    }

    /**
     * Инициализация lazy loading
     */
    function initializeLazyLoading() {
        const imageObserver = new IntersectionObserver(function(entries, observer) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        document.querySelectorAll('img[data-src]').forEach(function(img) {
            imageObserver.observe(img);
        });
    }

    /**
     * Утилита debounce
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = function() {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Экспорт функций в глобальную область видимости
    window.PhoneShop = {
        updateCartCount: updateCartCount,
        showNotification: showNotification,
        addToCart: function(productId, quantity) {
            handleAddToCart.call({ data: function() { return { productId: productId, quantity: quantity }; } });
        }
    };

})(jQuery);

/**
 * Дополнительные стили для JavaScript компонентов
 */
document.addEventListener('DOMContentLoaded', function() {
    // Добавляем CSS для динамических элементов
    const style = document.createElement('style');
    style.textContent = `
        .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s ease-in-out infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .search-suggestions {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            z-index: 1000;
            max-height: 300px;
            overflow-y: auto;
        }
        
        .suggestion-group {
            padding: 10px;
            border-bottom: 1px solid #eee;
        }
        
        .suggestion-group:last-child {
            border-bottom: none;
        }
        
        .suggestion-group h6 {
            margin: 0 0 5px 0;
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }
        
        .suggestion-item {
            padding: 5px 10px;
            cursor: pointer;
            border-radius: 4px;
            transition: background-color 0.2s;
        }
        
        .suggestion-item:hover {
            background-color: #f5f5f5;
        }
        
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
            animation: slideIn 0.3s ease-out;
        }
        
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        .loading {
            opacity: 0.6;
            pointer-events: none;
        }
        
        .lazy {
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        .lazy.loaded {
            opacity: 1;
        }
    `;
    document.head.appendChild(style);
});