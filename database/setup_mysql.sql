-- Создание базы данных для интернет-магазина мобильных телефонов
-- Phone Shop Database Setup Script

-- Создание базы данных
CREATE DATABASE IF NOT EXISTS phone_shop_db 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- Создание пользователя для приложения
CREATE USER IF NOT EXISTS 'phone_shop_user'@'localhost' IDENTIFIED BY 'PhoneShop2024!';
CREATE USER IF NOT EXISTS 'phone_shop_user'@'%' IDENTIFIED BY 'PhoneShop2024!';

-- Предоставление привилегий
GRANT ALL PRIVILEGES ON phone_shop_db.* TO 'phone_shop_user'@'localhost';
GRANT ALL PRIVILEGES ON phone_shop_db.* TO 'phone_shop_user'@'%';

-- Обновление привилегий
FLUSH PRIVILEGES;

-- Переключение на базу данных
USE phone_shop_db;

-- Установка режимов SQL для оптимальной производительности
SET sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO';
SET time_zone = '+00:00';

-- Создание таблиц будет выполнено через Django миграции
-- Этот скрипт только создает базу данных и пользователей