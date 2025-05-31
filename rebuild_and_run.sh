#!/bin/bash

echo "Проверка запущенных контейнеров..."

# Проверяем, запущен ли контейнер
if docker ps | grep -q duckly-container; then
    echo "Останавливаем запущенный контейнер duckly-container..."
    docker stop duckly-container
    echo "Контейнер остановлен."
fi

# Удаляем контейнер, если он существует
if docker ps -a | grep -q duckly-container; then
    echo "Удаляем существующий контейнер duckly-container..."
    docker rm duckly-container
    echo "Контейнер удален."
fi

# Создать директорию для сессий, если она не существует
echo "Создание директории для сессий..."
mkdir -p flask_session
chmod 777 flask_session
echo "Директория для сессий готова."

# Пересобрать образ
echo "Сборка Docker-образа..."
docker build -t duckly-app .
echo "Образ собран успешно."

# Запустить новый контейнер
echo "Запуск нового контейнера..."
docker run -d \
  --name duckly-container \
  -p 1800:1800 \
  -v $(pwd)/instance:/app/instance \
  -v $(pwd)/flask_session:/app/flask_session \
  -e SECRET_KEY='your-development-secret-key-here' \
  duckly-app

echo "==============================================="
echo "Приложение запущено на http://localhost:1800"
echo "==============================================="
echo "Логи контейнера (Ctrl+C для выхода):"
docker logs -f duckly-container