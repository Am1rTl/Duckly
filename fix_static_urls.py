#!/usr/bin/env python3
import os
import re

def fix_static_urls(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Заменяем {{ /static/... }} на /static/...
    content = re.sub(r"{{ /static/([^}]+) }}", r"/static/\1", content)
    
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

if __name__ == "__main__":
    process_templates()
    print("Static URL fixes completed!")