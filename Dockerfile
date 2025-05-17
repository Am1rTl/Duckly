FROM python:3.9-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 1800

CMD ["sh", "-c", "rm -f app.db && python site_1.py"]