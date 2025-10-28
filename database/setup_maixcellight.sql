-- PhoneShop - Настройка базы данных для MaixCellLight
-- Это адаптированная версия MySQL для новой архитектуры базы данных

-- Создание базы данных
CREATE DATABASE IF NOT EXISTS phone_shop_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE phone_shop_db;

-- Настройка MySQL для оптимальной производительности
SET sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO';

-- Создание пользователя и предоставление прав
CREATE USER IF NOT EXISTS 'phone_shop_user'@'localhost' IDENTIFIED BY 'PhoneShop2024!';
GRANT ALL PRIVILEGES ON phone_shop_db.* TO 'phone_shop_user'@'localhost';
GRANT SELECT ON mysql.* TO 'phone_shop_user'@'localhost';
FLUSH PRIVILEGES;

-- Основные таблицы будут созданы через Django миграции
-- Здесь приводим дополнительные настройки оптимизации

-- Настройка таблиц для максимальной производительности
SET GLOBAL innodb_buffer_pool_size = 512M;
SET GLOBAL innodb_log_file_size = 128M;
SET GLOBAL innodb_log_buffer_size = 32M;
SET GLOBAL innodb_flush_log_at_trx_commit = 2;

-- Оптимизация MySQL для интернет-магазина
SET GLOBAL query_cache_size = 64M;
SET GLOBAL tmp_table_size = 64M;
SET GLOBAL max_heap_table_size = 64M;

-- Настройка подключений
SET GLOBAL max_connections = 200;
SET GLOBAL interactive_timeout = 28800;
SET GLOBAL wait_timeout = 28800;

-- Оптимизация для высокой нагрузки
SET GLOBAL key_buffer_size = 256M;
SET GLOBAL bulk_insert_buffer_size = 32M;
SET GLOBAL read_buffer_size = 2M;
SET GLOBAL read_rnd_buffer_size = 8M;
SET GLOBAL sort_buffer_size = 8M;
SET GLOBAL myisam_sort_buffer_size = 64M;

-- Настройка кодировки по умолчанию
SET CHARACTER SET utf8mb4;
SET CHARACTER_SET_CONNECTION = utf8mb4;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Создание индексов для оптимизации поиска
-- Эти индексы будут добавлены автоматически через Django
-- Но можно создать дополнительные для специфичных запросов

-- Пример дополнительных индексов для производительности:
-- CREATE INDEX idx_product_name_search ON catalog_product (name(191));
-- CREATE INDEX idx_product_category_active ON catalog_product (category_id, is_active);
-- CREATE INDEX idx_product_price_range ON catalog_product (price, old_price);
-- CREATE INDEX idx_order_user_date ON orders_order (user_id, created_at);
-- CREATE INDEX idx_cart_session ON cart_cart (session_key, created_at);

-- Настройка триггеров для автоматических операций
-- (Будут добавлены через Django сигналы)

-- Создание представлений для аналитики (опционально)
-- CREATE VIEW product_sales_summary AS
-- SELECT 
--     p.id,
--     p.name,
--     p.price,
--     SUM(oi.quantity) as total_sold,
--     SUM(oi.quantity * oi.price) as total_revenue
-- FROM catalog_product p
-- JOIN orders_orderitem oi ON p.id = oi.product_id
-- JOIN orders_order o ON oi.order_id = o.id
-- WHERE o.status IN ('completed', 'shipped')
-- GROUP BY p.id, p.name, p.price;

-- Создание хранимых процедур для часто используемых операций
DELIMITER //

-- Процедура для получения популярных товаров
CREATE PROCEDURE GetPopularProducts(IN days_back INT, IN limit_count INT)
BEGIN
    SELECT 
        p.id,
        p.name,
        p.slug,
        p.price,
        p.old_price,
        p.rating,
        p.reviews_count,
        c.name as category_name,
        b.name as brand_name,
        COUNT(oi.id) as orders_count,
        SUM(oi.quantity) as total_sold
    FROM catalog_product p
    JOIN catalog_category c ON p.category_id = c.id
    JOIN catalog_brand b ON p.brand_id = b.id
    LEFT JOIN orders_orderitem oi ON p.id = oi.product_id
    LEFT JOIN orders_order o ON oi.order_id = o.id AND o.created_at >= DATE_SUB(NOW(), INTERVAL days_back DAY)
    WHERE p.is_active = 1
    GROUP BY p.id
    ORDER BY total_sold DESC
    LIMIT limit_count;
END //

-- Процедура для получения статистики продаж
CREATE PROCEDURE GetSalesStats(IN start_date DATE, IN end_date DATE)
BEGIN
    SELECT 
        DATE(o.created_at) as sale_date,
        COUNT(DISTINCT o.id) as orders_count,
        COUNT(DISTINCT o.user_id) as unique_customers,
        SUM(o.total_amount) as total_revenue,
        AVG(o.total_amount) as avg_order_value
    FROM orders_order o
    WHERE o.created_at BETWEEN start_date AND end_date
    AND o.status IN ('completed', 'shipped')
    GROUP BY DATE(o.created_at)
    ORDER BY sale_date;
END //

-- Процедура для обновления рейтинга товара
CREATE PROCEDURE UpdateProductRating(IN product_id INT)
BEGIN
    DECLARE avg_rating DECIMAL(3,2);
    
    SELECT AVG(rating) INTO avg_rating
    FROM catalog_review 
    WHERE product_id = product_id AND is_approved = 1;
    
    IF avg_rating IS NULL THEN
        SET avg_rating = 0.00;
    END IF;
    
    UPDATE catalog_product 
    SET 
        rating = ROUND(avg_rating, 2),
        reviews_count = (
            SELECT COUNT(*) 
            FROM catalog_review 
            WHERE product_id = product_id AND is_approved = 1
        )
    WHERE id = product_id;
END //

DELIMITER ;

-- Настройка cron jobs для автоматических операций
-- Эти задачи должны выполняться через внешний cron или celery

-- Ежедневное обновление статистики товаров
-- 0 2 * * * mysql -u phone_shop_user -pPhoneShop2024! phone_shop_db -e "CALL GetPopularProducts(30, 100);"

-- Очистка старых сессий корзины (старше 30 дней)
-- 0 3 * * * mysql -u phone_shop_user -pPhoneShop2024! phone_shop_db -e "DELETE FROM cart_cart WHERE session_key IS NULL AND created_at < DATE_SUB(NOW(), INTERVAL 30 DAY);"

-- Обновление рейтингов товаров
-- 0 4 * * * mysql -u phone_shop_user -pPhoneShop2024! phone_shop_db -e "UPDATE catalog_product SET rating = (SELECT AVG(rating) FROM catalog_review WHERE catalog_review.product_id = catalog_product.id AND is_approved = 1) WHERE id IN (SELECT DISTINCT product_id FROM catalog_review WHERE is_approved = 1);"

-- Настройка репликации (для продакшена)
-- Раскомментируйте в продакшене:
-- server-id = 1
-- log-bin = mysql-bin
-- binlog-do-db = phone_shop_db
-- sync_binlog = 1
-- innodb_flush_log_at_trx_commit = 1

-- Настройка бэкапа
-- mysqldump --single-transaction --routines --triggers phone_shop_db > backup_$(date +%Y%m%d_%H%M%S).sql

-- Настройка мониторинга производительности
-- Добавьте эти таблицы для мониторинга:
-- CREATE TABLE IF NOT EXISTS performance_stats (
--     id INT AUTO_INCREMENT PRIMARY KEY,
--     metric_name VARCHAR(100),
--     metric_value DECIMAL(15,2),
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     INDEX idx_metric_created (metric_name, created_at)
-- );

-- Создание триггера для логирования изменений заказов
DELIMITER //

CREATE TRIGGER order_status_change_log
AFTER UPDATE ON orders_order
FOR EACH ROW
BEGIN
    IF OLD.status != NEW.status THEN
        INSERT INTO orders_orderlog (order_id, old_status, new_status, changed_by, changed_at)
        VALUES (NEW.id, OLD.status, NEW.status, NEW.user_id, NOW());
    END IF;
END //

DELIMITER ;

-- Добавление комментариев к таблицам для документации
ALTER TABLE catalog_category COMMENT = 'Категории товаров - организация каталога по типам';
ALTER TABLE catalog_brand COMMENT = 'Бренды товаров - производители мобильных телефонов';
ALTER TABLE catalog_product COMMENT = 'Основная таблица товаров - мобильные телефоны и аксессуары';
ALTER TABLE orders_order COMMENT = 'Заказы покупателей - основная таблица транзакций';
ALTER TABLE cart_cart COMMENT = 'Корзины покупателей - временное хранение выбранных товаров';

-- Финальная настройка безопасности
FLUSH PRIVILEGES;

-- Проверка настроек
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';
SHOW VARIABLES LIKE 'max_connections';
SHOW VARIABLES LIKE 'query_cache_size';

SELECT 'MaixCellLight database setup completed successfully!' as message;

-- Создание тестовых данных (опционально)
-- Импортируйте тестовые данные через Django fixtures
-- python manage.py loaddata fixtures/initial_data.json