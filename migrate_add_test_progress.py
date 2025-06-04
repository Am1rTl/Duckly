#!/usr/bin/env python3
"""
Миграция для добавления таблицы test_progress
"""

import sqlite3
import os

def migrate_database():
    """Добавляет таблицу test_progress в базу данных"""
    
    # Пути к возможным базам данных
    db_paths = ['instance/app.db', 'app.db']
    db_path = None
    
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print(f"База данных не найдена по путям: {db_paths}")
        return False
    
    print(f"Используется база данных: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем, существует ли уже таблица
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='test_progress'
        """)
        
        if cursor.fetchone():
            print("Таблица test_progress уже существует")
            conn.close()
            return True
        
        # Создаем таблицу test_progress
        cursor.execute("""
            CREATE TABLE test_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_result_id INTEGER NOT NULL,
                test_word_id INTEGER NOT NULL,
                user_answer TEXT,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (test_result_id) REFERENCES test_results (id),
                FOREIGN KEY (test_word_id) REFERENCES test_words (id),
                UNIQUE(test_result_id, test_word_id)
            )
        """)
        
        # Создаем индексы для оптимизации
        cursor.execute("""
            CREATE INDEX idx_test_progress_result_id ON test_progress(test_result_id)
        """)
        
        cursor.execute("""
            CREATE INDEX idx_test_progress_word_id ON test_progress(test_word_id)
        """)
        
        conn.commit()
        print("Таблица test_progress успешно создана")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Ошибка при создании таблицы: {e}")
        return False

if __name__ == "__main__":
    print("Запуск миграции для добавления таблицы test_progress...")
    success = migrate_database()
    if success:
        print("Миграция завершена успешно!")
    else:
        print("Миграция завершилась с ошибкой!")