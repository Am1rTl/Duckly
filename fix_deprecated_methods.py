#!/usr/bin/env python3
"""
Скрипт для исправления deprecated методов SQLAlchemy в site_1.py
"""

import re

def fix_deprecated_methods():
    file_path = '/home/amir/Documents/Info/Duckly/site_1.py'
    
    # Читаем файл
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Заменяем User.query.get() на db.session.get(User, ...)
    content = re.sub(
        r'User\.query\.get\(([^)]+)\)',
        r'db.session.get(User, \1)',
        content
    )
    
    # Заменяем Test.query.get() на db.session.get(Test, ...)
    content = re.sub(
        r'Test\.query\.get\(([^)]+)\)',
        r'db.session.get(Test, \1)',
        content
    )
    
    # Заменяем Word.query.get() на db.session.get(Word, ...)
    content = re.sub(
        r'Word\.query\.get\(([^)]+)\)',
        r'db.session.get(Word, \1)',
        content
    )
    
    # Заменяем TestResult.query.get() на db.session.get(TestResult, ...)
    content = re.sub(
        r'TestResult\.query\.get\(([^)]+)\)',
        r'db.session.get(TestResult, \1)',
        content
    )
    
    # Заменяем TestProgress.query.get() на db.session.get(TestProgress, ...)
    content = re.sub(
        r'TestProgress\.query\.get\(([^)]+)\)',
        r'db.session.get(TestProgress, \1)',
        content
    )
    
    # Записываем обратно
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Deprecated методы SQLAlchemy исправлены!")

if __name__ == "__main__":
    fix_deprecated_methods()