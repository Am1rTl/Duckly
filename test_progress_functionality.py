#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функциональности сохранения прогресса
"""

import requests
import json

def test_progress_api():
    """Тестирует API сохранения и загрузки прогресса"""
    
    base_url = "http://localhost:1800"
    
    # Тестовые данные
    test_id = 1  # Замените на реальный ID теста
    
    # Данные для сохранения
    test_data = {
        "answers": [
            {
                "test_word_id": 1,
                "user_answer": "hello"
            },
            {
                "test_word_id": 2,
                "user_answer": "world"
            }
        ]
    }
    
    print("Тестирование API сохранения и загрузки прогресса...")
    
    # Тест сохранения прогресса
    print(f"\n1. Тестирование сохранения прогресса для теста {test_id}")
    try:
        response = requests.post(
            f"{base_url}/api/test/{test_id}/save_progress",
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        print(f"Статус ответа: {response.status_code}")
        print(f"Ответ: {response.text}")
    except Exception as e:
        print(f"Ошибка при сохранении: {e}")
    
    # Тест загрузки прогресса
    print(f"\n2. Тестирование загрузки прогресса для теста {test_id}")
    try:
        response = requests.get(f"{base_url}/api/test/{test_id}/load_progress")
        print(f"Статус ответа: {response.status_code}")
        print(f"Ответ: {response.text}")
    except Exception as e:
        print(f"Ошибка при загрузке: {e}")

if __name__ == "__main__":
    print("Запуск тестов функциональности прогресса...")
    test_progress_api()
    print("\nТестирование завершено!")