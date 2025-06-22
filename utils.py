import json
import random
import string
from datetime import datetime, timedelta
from functools import wraps
from flask import redirect, url_for, session, flash, jsonify
from models import db, User, Word, Test, TestResult, TestAnswer, TextContent, TextQuestion, TextTestAnswer
from config import Config

# Initialize config
config = Config()

def get_current_user():
    """Безопасное получение текущего пользователя с использованием современного API SQLAlchemy"""
    if 'user_id' not in session:
        return None
    return db.session.get(User, session['user_id'])

def generate_options_with_fallback(target_word, selected_modules, class_number, mode='word_to_translation'):
    """
    Генерирует 4 варианта ответов с приоритетным выбором из одного модуля.
    Эта функция сложная и может требовать специфичных параметров,
    которые не всегда доступны из utils. Она была в app.py, потому что имела доступ ко всем импортам.
    Придется передавать ей слова из БД или делать запросы внутри.
    Поскольку она используется только при создании тестов (в tests.py),
    ее можно переместить прямо в tests.py как внутреннюю helper-функцию
    или оставить здесь, убедившись, что у нее есть доступ к Word.query.
    """
    # target_word здесь - это словарь/объект, содержащий 'word' и 'perevod'
    correct_answer = target_word['perevod'] if mode == 'word_to_translation' else target_word['word']
    
    # Сначала пытаемся найти варианты из того же модуля
    same_module_words = Word.query.filter_by(
        classs=target_word['classs'],
        unit=target_word['unit'],
        module=target_word['module']
    ).filter(Word.id != target_word['id'] if 'id' in target_word else True).all()
    
    wrong_options = []
    
    # Берем варианты из того же модуля
    if same_module_words:
        options_from_module = [w.perevod if mode == 'word_to_translation' else w.word 
                             for w in same_module_words]
        # Избегаем дубликатов, если correct_answer тоже из этого модуля
        options_from_module = [opt for opt in options_from_module if opt != correct_answer]
        wrong_options.extend(random.sample(options_from_module, 
                                         min(3, len(options_from_module))))
    
    # Если недостаточно вариантов, добираем из других модулей того же юнита
    if len(wrong_options) < 3:
        same_unit_words = Word.query.filter_by(
            classs=target_word['classs'],
            unit=target_word['unit']
        ).filter(
            Word.id != target_word['id'] if 'id' in target_word else True,
            Word.module != target_word['module'] if 'module' in target_word else True # If module isn't specified, skip this filter
        ).all()
        
        if same_unit_words:
            options_from_unit = [w.perevod if mode == 'word_to_translation' else w.word 
                               for w in same_unit_words]
            options_from_unit = [opt for opt in options_from_unit if opt != correct_answer]
            needed = 3 - len(wrong_options)
            wrong_options.extend(random.sample(options_from_unit, 
                                             min(needed, len(options_from_unit))))
    
    # Если все еще недостаточно, берем из других юнитов того же класса
    if len(wrong_options) < 3:
        other_class_words = Word.query.filter_by(classs=target_word['classs']).filter(
            Word.id != target_word['id'] if 'id' in target_word else True,
        ).all()
        
        if other_class_words:
            options_from_class = [w.perevod if mode == 'word_to_translation' else w.word 
                                for w in other_class_words]
            options_from_class = [opt for opt in options_from_class if opt != correct_answer]
            needed = 3 - len(wrong_options)
            wrong_options.extend(random.sample(options_from_class, 
                                             min(needed, len(options_from_class))))
    
    # Заполняем недостающие варианты заглушками
    while len(wrong_options) < 3:
        # Для большей реалистичности, можно генерировать случайные слова, а не заглушки
        # Или брать из очень общего словаря
        wrong_options.append(f"Вариант {len(wrong_options) + 1}")
    
    # Создаем финальный список с правильным ответом
    all_options = wrong_options[:3] + [correct_answer]
    random.shuffle(all_options)
    
    return all_options

def format_time_taken(minutes):
    """
    Безопасно форматирует время выполнения теста для отображения.
    
    Args:
        minutes: Время в минутах (может быть None, 0 или отрицательным)
    
    Returns:
        str: Отформатированная строка времени
    """
    if minutes is None or minutes < 0:
        return "0 мин"
    
    if minutes == 0:
        return "<1 мин"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if hours == 0:
        return f"{remaining_minutes} мин"
    elif remaining_minutes == 0:
        return f"{hours} ч"
    else:
        return f"{hours} ч {remaining_minutes} мин"

def generate_options_with_fallback(target_word, selected_modules, class_number, mode='word_to_translation'):
    """
    Генерирует 4 варианта ответов с приоритетным выбором из одного модуля
    """
    correct_answer = target_word.perevod if mode == 'word_to_translation' else target_word.word
    
    # Сначала пытаемся найти варианты из того же модуля
    same_module_words = Word.query.filter_by(
        classs=target_word.classs,
        unit=target_word.unit,
        module=target_word.module
    ).filter(Word.id != target_word.id).all()
    
    wrong_options = []
    
    # Берем варианты из того же модуля
    if same_module_words:
        options_from_module = [w.perevod if mode == 'word_to_translation' else w.word 
                             for w in same_module_words]
        wrong_options.extend(random.sample(options_from_module, 
                                         min(3, len(options_from_module))))
    
    # Если недостаточно вариантов, добираем из других модулей того же юнита
    if len(wrong_options) < 3:
        same_unit_words = Word.query.filter_by(
            classs=target_word.classs,
            unit=target_word.unit
        ).filter(
            Word.id != target_word.id,
            Word.module != target_word.module
        ).all()
        
        if same_unit_words:
            options_from_unit = [w.perevod if mode == 'word_to_translation' else w.word 
                               for w in same_unit_words]
            needed = 3 - len(wrong_options)
            wrong_options.extend(random.sample(options_from_unit, 
                                             min(needed, len(options_from_unit))))
    
    # Если все еще недостаточно, берем из других юнитов того же класса
    if len(wrong_options) < 3:
        other_class_words = Word.query.filter_by(classs=target_word.classs).filter(
            Word.id != target_word.id,
            Word.unit != target_word.unit
        ).all()
        
        if other_class_words:
            options_from_class = [w.perevod if mode == 'word_to_translation' else w.word 
                                for w in other_class_words]
            needed = 3 - len(wrong_options)
            wrong_options.extend(random.sample(options_from_class, 
                                             min(needed, len(options_from_class))))
    
    # Заполняем недостающие варианты заглушками
    while len(wrong_options) < 3:
        wrong_options.append(f"Вариант {len(wrong_options) + 1}")
    
    # Создаем финальный список с правильным ответом
    all_options = wrong_options[:3] + [correct_answer]
    random.shuffle(all_options)
    
    return all_options

def auto_clear_previous_test_results(teacher_user, class_number, new_test_id):
    """
    Автоматически очищает результаты предыдущих тестов при создании нового теста.
    """
    if not AUTO_CLEAR_RESULTS_ON_NEW_TEST:
        return 0, []
    
    try:
        query = Test.query.filter(
            Test.created_by == teacher_user.id,
            Test.classs == class_number,
            Test.id != new_test_id
        )
        
        if CLEAR_ONLY_ACTIVE_TESTS:
            query = query.filter(Test.is_active == True)
        
        previous_tests = query.all()
        
        results_cleared_count = 0
        tests_affected = []
        
        for prev_test in previous_tests:
            results_to_delete = TestResult.query.filter_by(test_id=prev_test.id).all()
            
            if results_to_delete:
                tests_affected.append(prev_test.title)
                
                for result in results_to_delete:
                    TestAnswer.query.filter_by(test_result_id=result.id).delete(synchronize_session=False)
                    TextTestAnswer.query.filter_by(test_result_id=result.id).delete(synchronize_session=False)
                    db.session.delete(result)
                    results_cleared_count += 1
        
        if results_cleared_count > 0:
            db.session.commit()
        
        return results_cleared_count, tests_affected
        
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при автоматической очистке результатов: {e}")
        raise e
