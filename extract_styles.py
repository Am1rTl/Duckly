#!/usr/bin/env python3
"""
Скрипт для автоматического извлечения встроенных стилей из HTML файлов
и создания отдельных CSS файлов
"""

import os
import re
from pathlib import Path

# Настройки
TEMPLATES_DIR = Path("c:/Users/Djambek/OneDrive/Документы/Duckly/templates")
STATIC_CSS_DIR = Path("c:/Users/Djambek/OneDrive/Документы/Duckly/static/css")

# Категории файлов для организации CSS
FILE_CATEGORIES = {
    'auth': ['login', 'registration'],
    'games': ['game_', 'games'],
    'tests': ['test_', 'add_tests', 'configure_', 'take_test', 'tests'],
    'words': ['words', 'add_words', 'edit_word', 'module_'],
    'text_content': ['text_', 'create_text', 'edit_text'],
    'main': ['hello', 'about', 'profile', 'edit_profile', '404']
}

def determine_category(filename):
    """Определяет категорию файла на основе его имени"""
    filename = filename.lower()
    for category, patterns in FILE_CATEGORIES.items():
        for pattern in patterns:
            if pattern in filename:
                return category
    return 'common'

def extract_styles_from_file(html_file_path):
    """Извлекает стили из HTML файла"""
    with open(html_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Поиск тегов <style>
    style_pattern = r'<style[^>]*>(.*?)</style>'
    matches = re.findall(style_pattern, content, re.DOTALL)
    
    if not matches:
        return None, content
    
    # Объединяем все найденные стили
    extracted_styles = '\n'.join(matches)
    
    # Удаляем теги <style> из HTML
    cleaned_content = re.sub(style_pattern, '', content, flags=re.DOTALL)
    
    return extracted_styles.strip(), cleaned_content

def create_css_file(styles, css_file_path, filename):
    """Создаёт CSS файл с извлечёнными стилями"""
    # Добавляем комментарий с именем исходного файла
    css_content = f"/* Styles extracted from {filename} */\n{styles}"
    
    # Создаём директорию если её нет
    css_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(css_file_path, 'w', encoding='utf-8') as f:
        f.write(css_content)

def update_html_file(html_file_path, cleaned_content, css_relative_path):
    """Обновляет HTML файл, добавляя ссылку на CSS файл"""
    # Ищем место для вставки CSS ссылки (после последнего <link> или перед </head>)
    head_end_pattern = r'(</head>)'
    link_pattern = r'(<link[^>]*>)'
    
    css_link = f'    <link rel="stylesheet" href="{{{{ url_for(\'static\', filename=\'{css_relative_path}\') }}}}">'
    
    # Проверяем, есть ли уже другие <link> теги
    if re.search(link_pattern, cleaned_content):
        # Вставляем после последнего <link> тега
        links = list(re.finditer(link_pattern, cleaned_content))
        if links:
            last_link = links[-1]
            insert_pos = last_link.end()
            updated_content = (cleaned_content[:insert_pos] + 
                             f'\n{css_link}' + 
                             cleaned_content[insert_pos:])
        else:
            updated_content = re.sub(head_end_pattern, f'{css_link}\n\\1', cleaned_content)
    else:
        # Вставляем перед </head>
        updated_content = re.sub(head_end_pattern, f'{css_link}\n\\1', cleaned_content)
    
    with open(html_file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)

def process_html_files():
    """Основная функция для обработки всех HTML файлов"""
    processed_files = []
    skipped_files = []
    
    # Получаем все HTML файлы
    html_files = list(TEMPLATES_DIR.glob('*.html'))
    
    for html_file in html_files:
        filename = html_file.stem
        
        # Пропускаем уже обработанные файлы
        if filename in ['add_tests', 'login']:
            print(f"Пропускаем {filename}.html (уже обработан)")
            continue
        
        print(f"Обрабатываем {filename}.html...")
        
        # Извлекаем стили
        styles, cleaned_content = extract_styles_from_file(html_file)
        
        if not styles:
            print(f"  - В файле {filename}.html нет встроенных стилей")
            skipped_files.append(filename)
            continue
        
        # Определяем категорию и создаём путь для CSS файла
        category = determine_category(filename)
        css_filename = f"{filename}.css"
        css_file_path = STATIC_CSS_DIR / category / css_filename
        css_relative_path = f"css/{category}/{css_filename}"
        
        # Создаём CSS файл
        create_css_file(styles, css_file_path, filename)
        print(f"  - Создан CSS файл: {css_file_path}")
        
        # Обновляем HTML файл
        update_html_file(html_file, cleaned_content, css_relative_path)
        print(f"  - Обновлён HTML файл: {html_file}")
        
        processed_files.append(filename)
    
    print(f"\nОбработка завершена!")
    print(f"Обработано файлов: {len(processed_files)}")
    print(f"Пропущено файлов: {len(skipped_files)}")
    
    if processed_files:
        print(f"\nОбработанные файлы: {', '.join(processed_files)}")
    
    if skipped_files:
        print(f"Пропущенные файлы (без стилей): {', '.join(skipped_files)}")

if __name__ == "__main__":
    process_html_files()