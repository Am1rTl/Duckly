#!/usr/bin/env python3
"""
Скрипт для добавления поля allow_multiple_answers в таблицу text_questions
"""

import sqlite3
import os

def migrate_database():
    db_path = 'instance/app.db'
    
    if not os.path.exists(db_path):
        print(f"База данных не найдена по пути: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем, существует ли уже поле allow_multiple_answers
        cursor.execute("PRAGMA table_info(text_questions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'allow_multiple_answers' not in columns:
            print("Добавляем поле allow_multiple_answers...")
            cursor.execute("""
                ALTER TABLE text_questions 
                ADD COLUMN allow_multiple_answers BOOLEAN DEFAULT 0
            """)
            conn.commit()
            print("Поле allow_multiple_answers успешно добавлено!")
        else:
            print("Поле allow_multiple_answers уже существует.")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Ошибка при миграции базы данных: {e}")
        return False

if __name__ == "__main__":
    print("Запуск миграции базы данных...")
    if migrate_database():
        print("Миграция завершена успешно!")
    else:
        print("Миграция не удалась!")