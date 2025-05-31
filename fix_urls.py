#!/usr/bin/env python3
import os
import re

def fix_static_urls(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Заменяем url_for('static', filename='...') на /static/...
    content = re.sub(r"url_for\('static', filename='([^']+)'\)", r"/static/\1", content)
    content = re.sub(r'url_for\("static", filename="([^"]+)"\)', r'/static/\1', content)
    
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)

def fix_route_urls(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Заменяем url_for('hello') на /hello
    content = re.sub(r"url_for\('hello'\)", r'"/hello"', content)
    content = re.sub(r'url_for\("hello"\)', r'"/hello"', content)
    
    # Заменяем url_for('tests') на /tests
    content = re.sub(r"url_for\('tests'\)", r'"/tests"', content)
    content = re.sub(r'url_for\("tests"\)', r'"/tests"', content)
    
    # Заменяем url_for('games') на /games
    content = re.sub(r"url_for\('games'\)", r'"/games"', content)
    content = re.sub(r'url_for\("games"\)', r'"/games"', content)
    
    # Заменяем url_for('flashcards_select_module') на /flashcards_select_module
    content = re.sub(r"url_for\('flashcards_select_module'\)", r'"/flashcards_select_module"', content)
    
    # Заменяем url_for('word_match_select_module') на /word_match_select_module
    content = re.sub(r"url_for\('word_match_select_module'\)", r'"/word_match_select_module"', content)
    
    # Заменяем url_for('sentence_scramble_select_module') на /sentence_scramble_select_module
    content = re.sub(r"url_for\('sentence_scramble_select_module'\)", r'"/sentence_scramble_select_module"', content)
    
    # Заменяем url_for('add_tests') на /add_tests
    content = re.sub(r"url_for\('add_tests'\)", r'"/add_tests"', content)
    
    # Заменяем url_for('create_test') на /create_test
    content = re.sub(r"url_for\('create_test'\)", r'"/create_test"', content)
    
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)

def process_templates():
    templates_dir = '/home/amir/Documents/Info/Duckly/templates'
    for root, _, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                print(f"Processing {file_path}")
                fix_static_urls(file_path)
                fix_route_urls(file_path)

if __name__ == "__main__":
    process_templates()
    print("URL fixes completed!")