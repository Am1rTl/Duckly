FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей и устанавливаем их (включая gunicorn)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Копируем весь код проекта (включая файлы: site_1.py, create_db.py, Dockerfile и папки instance, templates, static и nginx_config)
COPY . .

# Открываем порт 1800, на котором будет работать Gunicorn
EXPOSE 1800

# Запускаем Gunicorn, указывая имя модуля и объекта приложения (предполагаем site_1.py с объектом app)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:1800", "site_1:app"]