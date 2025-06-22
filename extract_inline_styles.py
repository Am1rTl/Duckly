#!/usr/bin/env python3
"""
Скрипт для извлечения inline стилей из HTML файлов 
и добавления их в соответствующие CSS файлы
"""

import os
import re
from pathlib import Path
from collections import defaultdict

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

def extract_inline_styles(html_content):
    """Извлекает все inline стили из HTML"""
    # Паттерн для поиска style атрибутов
    style_pattern = r'style="([^"]*)"'
    matches = re.findall(style_pattern, html_content, re.IGNORECASE)
    
    # Собираем уникальные стили
    unique_styles = set()
    style_map = {}  # Для замены inline стилей на классы
    
    for i, style in enumerate(matches):
        if style.strip():
            unique_styles.add(style.strip())
            # Создаём имя класса на основе номера
            class_name = f"inline-style-{i+1}"
            style_map[style] = class_name
    
    return list(unique_styles), style_map

def create_css_classes(styles, class_prefix="inline-style"):
    """Создаёт CSS классы из inline стилей"""
    css_rules = []
    for i, style in enumerate(styles):
        class_name = f"{class_prefix}-{i+1}"
        css_rule = f".{class_name} {{ {style} }}"
        css_rules.append(css_rule)
    
    return css_rules

def replace_inline_styles(html_content, style_map):
    """Заменяет inline стили на CSS классы"""
    for style, class_name in style_map.items():
        # Ищем и заменяем style="..." на class="..."
        pattern = rf'style="{re.escape(style)}"'
        # Проверяем, есть ли уже атрибут class
        # Это упрощённая версия - может потребоваться более сложная логика
        replacement = f'class="{class_name}"'
        html_content = re.sub(pattern, replacement, html_content, flags=re.IGNORECASE)
    
    return html_content

def append_to_css_file(css_file_path, new_css_rules):
    """Добавляет новые CSS правила в существующий файл"""
    if not css_file_path.exists():
        return False
    
    with open(css_file_path, 'a', encoding='utf-8') as f:
        f.write('\n\n/* Inline styles converted to classes */\n')
        for rule in new_css_rules:
            f.write(rule + '\n')
    
    return True

def process_file_inline_styles(html_file_path):
    """Обрабатывает inline стили в одном файле"""
    filename = html_file_path.stem
    
    # Читаем HTML файл
    with open(html_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Извлекаем inline стили
    styles, style_map = extract_inline_styles(html_content)
    
    if not styles:
        return False, "Нет inline стилей"
    
    # Определяем категорию и путь к CSS файлу
    category = determine_category(filename)
    css_filename = f"{filename}.css"
    css_file_path = STATIC_CSS_DIR / category / css_filename
    
    # Создаём CSS классы
    css_rules = create_css_classes(styles)
    
    # Добавляем CSS правила в файл
    success = append_to_css_file(css_file_path, css_rules)
    
    if not success:
        return False, f"CSS файл не найден: {css_file_path}"
    
    # Заменяем inline стили в HTML (опционально)
    # updated_html = replace_inline_styles(html_content, style_map)
    # 
    # with open(html_file_path, 'w', encoding='utf-8') as f:
    #     f.write(updated_html)
    
    return True, f"Добавлено {len(styles)} inline стилей в {css_file_path}"

def analyze_inline_styles():
    """Анализирует все inline стили в проекте"""
    print("Анализ inline стилей в HTML файлах...")
    
    # Собираем статистику
    total_files = 0
    processed_files = 0
    total_styles = 0
    
    style_stats = defaultdict(int)
    
    # Получаем все HTML файлы
    html_files = list(TEMPLATES_DIR.glob('*.html'))
    
    for html_file in html_files:
        total_files += 1
        filename = html_file.stem
        
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Подсчитываем inline стили
        style_matches = re.findall(r'style="([^"]*)"', content, re.IGNORECASE)
        
        if style_matches:
            processed_files += 1
            file_styles = len(style_matches)
            total_styles += file_styles
            
            print(f"\n{filename}.html:")
            print(f"  - Найдено inline стилей: {file_styles}")
            
            # Показываем несколько примеров
            for i, style in enumerate(style_matches[:3]):  # Показываем первые 3
                print(f"    {i+1}. {style}")
            
            if len(style_matches) > 3:
                print(f"    ... и ещё {len(style_matches) - 3}")
            
            # Собираем статистику по типам стилей
            for style in style_matches:
                if 'display:' in style:
                    style_stats['display'] += 1
                if 'margin' in style:
                    style_stats['margin'] += 1
                if 'padding' in style:
                    style_stats['padding'] += 1
                if 'color' in style:
                    style_stats['color'] += 1
                if 'background' in style:
                    style_stats['background'] += 1
    
    print(f"\n" + "="*50)
    print(f"СТАТИСТИКА INLINE СТИЛЕЙ:")
    print(f"="*50)
    print(f"Всего файлов проверено: {total_files}")
    print(f"Файлов с inline стилями: {processed_files}")
    print(f"Общее количество inline стилей: {total_styles}")
    
    if style_stats:
        print(f"\nТипы стилей:")
        for style_type, count in sorted(style_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  {style_type}: {count}")

if __name__ == "__main__":
    analyze_inline_styles()