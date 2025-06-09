#!/usr/bin/env python3
"""
Скрипт миграции для обеспечения совместимости поля text_based_questions
"""

import sqlite3
import os

def migrate_text_questions():
    db_path = '/home/amir/Documents/Info/Duckly/instance/app.db'
    
    if not os.path.exists(db_path):
        print("База данных не найдена. Создайте её сначала.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверяем, существует ли столбец text_based_questions
        cursor.execute("PRAGMA table_info(tests)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'text_based_questions' not in columns:
            print("Добавляем столбец text_based_questions...")
            cursor.execute("ALTER TABLE tests ADD COLUMN text_based_questions TEXT")
            conn.commit()
            print("Столбец text_based_questions добавлен успешно!")
        else:
            print("Столбец text_based_questions уже существует.")
        
        # Проверяем, существует ли столбец text_content
        if 'text_content' not in columns:
            print("Добавляем столбец text_content...")
            cursor.execute("ALTER TABLE tests ADD COLUMN text_content TEXT")
            conn.commit()
            print("Столбец text_content добавлен успешно!")
        else:
            print("Столбец text_content уже существует.")
            
    except Exception as e:
        print(f"Ошибка при миграции: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_text_questions()