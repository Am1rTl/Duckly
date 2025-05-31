FROM python:3.9-slim

WORKDIR /app
COPY . .

# Print confirmation message and show directory structure
RUN echo "Files successfully copied to container!" && \
    find /app -type f -not -path "*/\.*" | sort

# Create instance directory for SQLite database
RUN mkdir -p /app/instance && \
    touch /app/instance/app.db && \
    chmod 777 /app/instance/app.db

# Create directory for Flask sessions
RUN mkdir -p /app/flask_session && \
    chmod 777 /app/flask_session

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Установка переменных окружения
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV FLASK_APP=site_1.py

EXPOSE 1800

# Запуск приложения с явным указанием хоста и порта
CMD ["python", "site_1.py"]