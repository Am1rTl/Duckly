#!/bin/bash

echo "Остановка и удаление существующего контейнера..."
docker stop duckly-container 2>/dev/null || true
docker rm duckly-container 2>/dev/null || true

echo "Создание директорий для данных..."
mkdir -p instance
mkdir -p flask_session
chmod 777 instance
chmod 777 flask_session

echo "Сборка Docker-образа..."
docker build -t duckly-app .

echo "Запуск контейнера..."
docker run -d \
  --name duckly-container \
  -p 1800:1800 \
  -v $(pwd)/instance:/app/instance \
  -v $(pwd)/flask_session:/app/flask_session \
  -e SECRET_KEY='super-secret-key-for-duckly-app' \
  duckly-app

echo "Контейнер запущен. Приложение доступно по адресу: http://localhost:1800"
echo "Логи контейнера:"
docker logs -f duckly-container