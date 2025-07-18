from markupsafe import escape
from flask import Flask, jsonify, request, render_template, redirect, url_for, flash, make_response, session, abort, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash # Added for password hashing
from flask_session import Session  # Добавляем поддержку сессий на основе файловой системы
import time
import sqlite3
import random
import string
from datetime import datetime, timedelta
import json
import subprocess # Added to run external scripts
import re # Add this at the top with other imports
import os # Added for os.makedirs
import tempfile # Для временных файлов сессии

# Import models and db
from models import db, User, Word, Test, TestWord, TestResult, TestAnswer, TestProgress, UserWordReview, Sentence, TextContent, TextQuestion, TextTestAnswer

# Настройки автоматической очистки результатов
AUTO_CLEAR_RESULTS_ON_NEW_TEST = True  # Включить/выключить автоматическую очистку
CLEAR_ONLY_ACTIVE_TESTS = True  # Очищать только активные тесты (сохранять архивированные)

def get_current_user():
    """Безопасное получение текущего пользователя с использованием современного API SQLAlchemy"""
    if 'user_id' not in session:
        return None
    
    # Использование db.session.get() вместо User.query.get()
    return db.session.get(User, session['user_id'])

def require_login(f):
    """Декоратор для проверки авторизации"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def require_teacher(f):
    """Декоратор для проверки прав учителя"""
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or user.teacher != 'yes':
            flash('Доступ запрещён. Требуются права учителя.', 'error')
            return redirect(url_for('hello'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


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

def auto_clear_previous_test_results(teacher_user, class_number, new_test_id):
    """
    Автоматически очищает результаты предыдущих тестов при создании нового теста.
    
    Args:
        teacher_user: Объект пользователя-учителя
        class_number: Номер класса
        new_test_id: ID нового теста (исключается из очистки)
    
    Returns:
        tuple: (количество_очищенных_результатов, список_затронутых_тестов)
    """
    if not AUTO_CLEAR_RESULTS_ON_NEW_TEST:
        return 0, []
    
    try:
        # Строим запрос для поиска предыдущих тестов
        query = Test.query.filter(
            Test.created_by == teacher_user.id,
            Test.classs == class_number,
            Test.id != new_test_id
        )
        
        # Если настроено очищать только активные тесты
        if CLEAR_ONLY_ACTIVE_TESTS:
            query = query.filter(Test.is_active == True)
        
        previous_tests = query.all()
        
        results_cleared_count = 0
        tests_affected = []
        
        for prev_test in previous_tests:
            # Находим все результаты для этого теста
            results_to_delete = TestResult.query.filter_by(test_id=prev_test.id).all()
            
            if results_to_delete:  # Если есть результаты для удаления
                tests_affected.append(prev_test.title)
                
                for result in results_to_delete:
                    # Удаляем связанные ответы
                    TestAnswer.query.filter_by(test_result_id=result.id).delete(synchronize_session=False)
                    # Удаляем ответы для текстовых тестов
                    TextTestAnswer.query.filter_by(test_result_id=result.id).delete(synchronize_session=False)
                    # Удаляем результат
                    db.session.delete(result)
                    results_cleared_count += 1
        
        if results_cleared_count > 0:
            db.session.commit()
        
        return results_cleared_count, tests_affected
        
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при автоматической очистке результатов: {e}")
        raise e

app = Flask(__name__)
# Create instance folder if it doesn't exist
try:
    os.makedirs(app.instance_path, exist_ok=True)
except OSError as e:
    print(f"Error creating instance directory {app.instance_path}: {e}")

# Определяем путь к базе данных в зависимости от окружения
if os.path.exists('/app'):
    # Запуск в Docker
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////app/instance/app.db'
else:
    # Локальный запуск
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(app.instance_path, "app.db")}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'a-default-development-secret-key')  # Load secret key from env var

# Настройка сессии для работы в Docker
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=15)
app.config['SESSION_USE_SIGNER'] = True  # Подписываем cookie для безопасности
app.config['SESSION_KEY_PREFIX'] = 'duckly_'  # Префикс для файлов сессий

# Определяем директорию для хранения сессий
if os.path.exists('/app'):
    # В Docker используем постоянную директорию
    session_dir = '/app/flask_session'
    if not os.path.exists(session_dir):
        os.makedirs(session_dir, exist_ok=True)
    app.config['SESSION_FILE_DIR'] = session_dir
else:
    # Локально используем временную директорию
    app.config['SESSION_FILE_DIR'] = tempfile.gettempdir()

# Настройка cookie для сессии
app.config['SESSION_COOKIE_NAME'] = 'duckly_session'
app.config['SESSION_COOKIE_SECURE'] = False  # Установите True в production с HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_PATH'] = '/'

# Инициализация сессии
Session(app)

# Initialize the db with the app
db.init_app(app)

# Import blueprints after app and db initialization to avoid circular imports
from blueprints.auth import auth_bp
from blueprints.words import words_bp

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(words_bp)

# Add custom template filters
@app.template_filter('from_json')
def from_json_filter(value):
    """Convert JSON string to Python object"""
    try:
        return json.loads(value) if value else []
    except (json.JSONDecodeError, TypeError):
        return []

# Models are now imported from models.py


@app.route("/")
def index():
    return redirect('/hello', 302)

@app.route("/user/<name>")
def greet(name):
    return f"Hello, {name}!"

@app.route("/create_text_based_test/<int:test_id>", methods=['GET', 'POST'])
@require_login
@require_teacher
def create_text_based_test(test_id):
    """Создание вопросов для теста на основе текста"""
    # Использование db.session.get() вместо Test.query.get()
    test = db.session.get(Test, test_id)
    if not test:
        flash('Тест не найден', 'error')
        return redirect(url_for('tests'))
    
    current_user = get_current_user()
    if test.created_by != current_user.id:
        flash('У вас нет прав для редактирования этого теста', 'error')
        return redirect(url_for('tests'))
    
    if request.method == 'POST':
        questions_data = request.form.get('questions_data')
        if questions_data:
            try:
                questions = json.loads(questions_data)
                # Сохранение вопросов в поле text_based_questions
                test.text_based_questions = json.dumps(questions, ensure_ascii=False)
                db.session.commit()
                flash('Вопросы успешно сохранены!', 'success')
                return redirect(url_for('test_details', test_id=test.id))
            except json.JSONDecodeError:
                flash('Ошибка при сохранении вопросов', 'error')
        else:
            # Если нет данных, сохраняем пустой список
            test.text_based_questions = json.dumps([], ensure_ascii=False)
            db.session.commit()
            flash('Вопросы очищены', 'info')
            return redirect(url_for('test_details', test_id=test.id))
    
    # Получение существующих вопросов
    existing_questions = []
    if test.text_based_questions:
        try:
            existing_questions = json.loads(test.text_based_questions)
        except json.JSONDecodeError:
            existing_questions = []
    
    # Подготовка данных для JavaScript
    questions_for_js = json.dumps(existing_questions, ensure_ascii=False)
    
    return render_template('configure_text_quiz.html', 
                         test=test, 
                         questions_for_js=questions_for_js)

@app.route('/take_text_test/<test_link>')
@require_login
def take_text_test(test_link):
    """Прохождение теста на основе текста"""
    # Использование современного API SQLAlchemy
    test = db.session.execute(
        db.select(Test).where(Test.link == test_link)
    ).scalar_one_or_none()
    
    if not test:
        flash('Тест не найден', 'error')
        return redirect(url_for('hello'))
    
    if not test.is_active:
        flash('Тест неактивен', 'error')
        return redirect(url_for('hello'))
    
    # Проверка наличия вопросов - сначала пробуем новую структуру
    questions = []
    if test.text_content_id:
        # Используем новую структуру с TextQuestion
        text_questions = db.session.execute(
            db.select(TextQuestion).where(
                TextQuestion.text_content_id == test.text_content_id
            ).order_by(TextQuestion.order_number)
        ).scalars().all()
        
        questions = []
        for tq in text_questions:
            question_data = {
                'id': tq.id,
                'question': tq.question,
                'type': tq.question_type,
                'correct_answer': tq.correct_answer,
                'points': tq.points
            }
            if tq.options:
                try:
                    question_data['options'] = json.loads(tq.options)
                except json.JSONDecodeError:
                    question_data['options'] = []
            questions.append(question_data)
    elif test.text_based_questions:
        # Fallback к старой структуре
        try:
            questions = json.loads(test.text_based_questions)
        except json.JSONDecodeError:
            questions = []
    
    if not questions:
        flash('В тесте нет вопросов', 'error')
        return redirect(url_for('hello'))
    
    current_user = get_current_user()
    
    # Проверка существующего результата с использованием современного API
    existing_result = db.session.execute(
        db.select(TestResult).where(
            TestResult.test_id == test.id,
            TestResult.user_id == current_user.id,
            TestResult.completed_at.is_(None)
        )
    ).scalar_one_or_none()
    
    if existing_result:
        # Продолжение существующего теста
        test_result = existing_result
    else:
        # Создание нового результата теста
        test_result = TestResult(
            test_id=test.id,
            user_id=current_user.id,
            total_questions=len(questions),
            started_at=datetime.utcnow()
        )
        db.session.add(test_result)
        db.session.commit()
    
    # Получаем текстовый контент
    text_content = None
    if test.text_content_id:
        text_content = db.session.get(TextContent, test.text_content_id)
    
    return render_template('take_text_test.html', 
                         test=test, 
                         questions=questions,
                         test_result=test_result,
                         text_content=text_content)

@app.route('/submit_text_test/<int:test_result_id>', methods=['POST'])
@require_login
def submit_text_test(test_result_id):
    """Обработка ответов на тест с текстом"""
    # Использование db.session.get() вместо TestResult.query.get()
    test_result = db.session.get(TestResult, test_result_id)
    if not test_result:
        return jsonify({'error': 'Результат теста не найден'}), 404
    
    current_user = get_current_user()
    if test_result.user_id != current_user.id:
        return jsonify({'error': 'Доступ запрещён'}), 403
    
    if test_result.completed_at:
        return jsonify({'error': 'Тест уже завершён'}), 400
    
    test = db.session.get(Test, test_result.test_id)
    
    # Получаем вопросы - сначала пробуем новую структуру
    questions = []
    if test.text_content_id:
        # Используем новую структуру с TextQuestion
        text_questions = db.session.execute(
            db.select(TextQuestion).where(
                TextQuestion.text_content_id == test.text_content_id
            ).order_by(TextQuestion.order_number)
        ).scalars().all()
        
        questions = text_questions
    elif test.text_based_questions:
        # Fallback к старой структуре
        try:
            old_questions = json.loads(test.text_based_questions)
            # Преобразуем в объекты для совместимости
            questions = []
            for i, q in enumerate(old_questions):
                class OldQuestion:
                    def __init__(self, data, index):
                        self.id = f"old_{index}"
                        self.question = data.get('question', '')
                        self.question_type = data.get('type', 'open_answer')
                        self.correct_answer = data.get('correct', '')
                        self.points = 1
                        self.options = data.get('options', [])
                questions.append(OldQuestion(q, i))
        except json.JSONDecodeError:
            questions = []
    
    # Получение ответов из формы и подсчет правильных ответов
    correct_count = 0
    total_points = 0
    earned_points = 0
    
    for i, question in enumerate(questions):
        question_key = f'question_{i}'
        user_answer = request.form.get(question_key, '').strip()
        
        # Проверка правильности ответа
        is_correct = False
        points_for_question = getattr(question, 'points', 1)
        total_points += points_for_question
        
        if question.question_type == 'multiple_choice':
            is_correct = user_answer == question.correct_answer
        elif question.question_type == 'multiple_select':
            # Для множественного выбора сравниваем JSON массивы
            try:
                user_answers = json.loads(user_answer) if user_answer else []
                correct_answers = json.loads(question.correct_answer) if question.correct_answer else []
                # Сравниваем отсортированные списки для корректного сравнения
                is_correct = sorted(user_answers) == sorted(correct_answers)
            except json.JSONDecodeError:
                is_correct = False
        elif question.question_type == 'true_false':
            # Поддержка "Да", "Нет", "Не указано"
            is_correct = user_answer == question.correct_answer
        elif question.question_type == 'open_answer':
            # Для открытых вопросов проверяем точное совпадение (можно улучшить)
            is_correct = user_answer.lower().strip() == question.correct_answer.lower().strip()
        
        if is_correct:
            correct_count += 1
            earned_points += points_for_question
        
        # Сохраняем ответ в новой структуре, если используем TextQuestion
        if hasattr(question, 'id') and isinstance(question.id, int):
            text_answer = TextTestAnswer(
                test_result_id=test_result.id,
                text_question_id=question.id,
                user_answer=user_answer,
                is_correct=is_correct,
                points_earned=points_for_question if is_correct else 0
            )
            db.session.add(text_answer)
    
    # Обновление результата теста
    test_result.correct_answers = correct_count
    test_result.score = int((earned_points / total_points) * 100) if total_points > 0 else 0
    test_result.completed_at = datetime.utcnow()
    
    # Вычисляем время выполнения
    if test_result.started_at:
        time_diff = datetime.utcnow() - test_result.started_at
        test_result.time_taken = max(0, int(time_diff.total_seconds() / 60))
    else:
        test_result.time_taken = 0
    
    db.session.commit()
    
    return redirect(url_for('view_text_test_result', test_result_id=test_result.id))

@app.route('/view_text_test_result/<int:test_result_id>')
@require_login
def view_text_test_result(test_result_id):
    """Просмотр результатов теста на основе текста"""
    # Использование db.session.get() вместо TestResult.query.get()
    test_result = db.session.get(TestResult, test_result_id)
    if not test_result:
        flash('Результат теста не найден', 'error')
        return redirect(url_for('hello'))
    
    current_user = get_current_user()
    
    # Проверка прав доступа
    if test_result.user_id != current_user.id and current_user.teacher != 'yes':
        flash('Доступ запрещён', 'error')
        return redirect(url_for('hello'))
    
    test = db.session.get(Test, test_result.test_id)
    
    # Получаем текстовый контент
    text_content = None
    if test.text_content_id:
        text_content = db.session.get(TextContent, test.text_content_id)
    
    # Получаем вопросы и ответы - сначала пробуем новую структуру
    detailed_results = []
    
    if test.text_content_id:
        # Используем новую структуру с TextQuestion и TextTestAnswer
        text_questions = db.session.execute(
            db.select(TextQuestion).where(
                TextQuestion.text_content_id == test.text_content_id
            ).order_by(TextQuestion.order_number)
        ).scalars().all()
        
        for i, question in enumerate(text_questions):
            # Получаем ответ пользователя
            text_answer = db.session.execute(
                db.select(TextTestAnswer).where(
                    TextTestAnswer.test_result_id == test_result.id,
                    TextTestAnswer.text_question_id == question.id
                )
            ).scalar_one_or_none()
            
            user_answer = text_answer.user_answer if text_answer else ''
            is_correct = text_answer.is_correct if text_answer else False
            points_earned = text_answer.points_earned if text_answer else 0
            
            # Получаем варианты ответов для multiple_choice
            options = []
            if question.options:
                try:
                    options = json.loads(question.options)
                except json.JSONDecodeError:
                    options = []
            
            detailed_results.append({
                'question': question,
                'user_answer': user_answer,
                'is_correct': is_correct,
                'points_earned': points_earned,
                'question_number': i + 1,
                'options': options
            })
    
    elif test.text_based_questions:
        # Fallback к старой структуре
        try:
            questions = json.loads(test.text_based_questions)
        except json.JSONDecodeError:
            questions = []
        
        # Получение ответов пользователя из старой структуры
        user_answers = {}
        if test_result.answers:
            try:
                user_answers = json.loads(test_result.answers)
            except json.JSONDecodeError:
                user_answers = {}
        
        for i, question in enumerate(questions):
            question_key = f'question_{i}'
            user_answer = user_answers.get(question_key, '')
            
            # Определение правильности ответа (старая логика)
            is_correct = False
            if question.get('type') == 'mc_single':
                is_correct = user_answer in question.get('correct', [])
            elif question.get('type') == 'mc_multiple':
                if isinstance(user_answer, list):
                    correct_answers = set(question.get('correct', []))
                    user_answers_set = set(user_answer)
                    is_correct = user_answers_set == correct_answers
            elif question.get('type') == 'short_answer':
                correct_answers = question.get('correct', [])
                is_correct = any(user_answer.lower() == correct.lower() for correct in correct_answers)
            
            detailed_results.append({
                'question': question,
                'user_answer': user_answer,
                'is_correct': is_correct,
                'question_number': i + 1,
                'points_earned': 1 if is_correct else 0
            })
    
    # Вычисляем статистику из detailed_results
    correct_count = sum(1 for result in detailed_results if result['is_correct'])
    earned_points = sum(result['points_earned'] for result in detailed_results)
    
    # Для новой структуры используем реальные баллы, для старой - по 1 баллу за вопрос
    if test.text_content_id:
        # Новая структура - используем реальные баллы из вопросов
        total_points = sum(result['question'].points if hasattr(result['question'], 'points') else 1 
                          for result in detailed_results)
    else:
        # Старая структура - каждый вопрос стоит 1 балл
        total_points = len(detailed_results)
    
    # Обновление результата теста
    test_result.correct_answers = correct_count
    test_result.score = int((earned_points / total_points) * 100) if total_points > 0 else 0
    test_result.completed_at = datetime.utcnow()
    
    # Вычисляем время выполнения
    if test_result.started_at:
        time_diff = datetime.utcnow() - test_result.started_at
        test_result.time_taken = max(0, int(time_diff.total_seconds() / 60))
    else:
        test_result.time_taken = 0
    
    db.session.commit()
    
    return render_template('view_text_test_result.html',
                         test_result=test_result,
                         test=test,
                         text_content=text_content,
                         detailed_results=detailed_results,
                         current_user=current_user)



@app.route("/add_tests", methods=['POST', 'GET'])
def add_tests():
    if 'user_id' not in session:
        flash("Доступ запрещен. Пожалуйста, войдите как учитель.", "warning")
        return redirect(url_for('auth.login'))

    user = db.session.get(User, session['user_id'])
    if not user or user.teacher != 'yes':
        flash("Доступ запрещен. Только учителя могут добавлять тесты.", "warning")
        if not user:
            session.pop('user_id', None)
        return redirect(url_for('auth.login'))
    
    if request.method == "POST":
        test_type = request.form.get('test_type')
        test_direction = request.form.get('test_direction', 'word_to_translation')
        text_content = request.form.get('text_content', '')
        class_number = request.form.get('class_number')
        title = request.form.get('title')
        
        time_limit_str = request.form.get('time_limit')
        time_limit = int(time_limit_str) if time_limit_str and time_limit_str.isdigit() and int(time_limit_str) > 0 else None
        
        word_order_form = request.form.get('word_order', 'sequential') 
        word_count_form_str = request.form.get('word_count')
        word_count_form = int(word_count_form_str) if word_count_form_str and word_count_form_str.isdigit() and int(word_count_form_str) > 0 else None
        test_mode = request.form.get('test_mode', 'random_letters') if test_type == 'add_letter' else None
        
        new_test_params = {
            'title': title,
            'classs': class_number,
            'type': test_type,
            'test_direction': test_direction,
            'text_content': text_content,
            'link': generate_test_link(),
            'created_by': user.id,
            'time_limit': time_limit,
            'word_order': word_order_form,
            'test_mode': test_mode,
            'is_active': True
        }

        words_data_source = []
        word_source_type = request.form.get('word_source_type', 'modules_only')
        selected_module_identifiers = []
        if word_source_type in ['modules_only', 'modules_and_custom']:
            selected_module_identifiers = request.form.getlist('modules[]')

        custom_words_text = []
        custom_translations_text = []
        if word_source_type in ['custom_only', 'modules_and_custom']:
            custom_words_text = request.form.getlist('custom_words[]')
            custom_translations_text = request.form.getlist('custom_translations[]')

        module_words_list = []
        if selected_module_identifiers:
            for module_identifier in selected_module_identifiers:
                try:
                    class_num, unit, module_name = module_identifier.split('|')
                    module_words_db = Word.query.filter_by(classs=class_num, unit=unit, module=module_name).all()
                    for mw in module_words_db:
                        module_words_list.append({'id': mw.id, 'word': mw.word, 'perevod': mw.perevod, 'source': 'module'})
                except ValueError:
                    flash(f"Некорректный идентификатор модуля: {module_identifier}", "warning")

        if test_type == 'dictation':
            dictation_word_source = request.form.get('dictation_word_source')
            new_test_params['dictation_word_source'] = dictation_word_source
            if dictation_word_source == 'all_module':
                words_data_source.extend(module_words_list)
                new_test_params['word_count'] = word_count_form
            elif dictation_word_source == 'random_from_module':
                dictation_num_random_words_str = request.form.get('dictation_random_word_count')
                dictation_num_random_words = int(dictation_num_random_words_str) if dictation_num_random_words_str and dictation_num_random_words_str.isdigit() and int(dictation_num_random_words_str) > 0 else 0
                new_test_params['word_count'] = dictation_num_random_words if dictation_num_random_words > 0 else None
                if module_words_list and dictation_num_random_words > 0:
                    random.shuffle(module_words_list)
                    words_data_source.extend(module_words_list[:dictation_num_random_words])
            elif dictation_word_source == 'selected_specific':
                specific_word_ids_str = request.form.getlist('dictation_specific_word_ids[]')
                specific_word_ids = [int(id_str) for id_str in specific_word_ids_str if id_str.isdigit()]
                new_test_params['dictation_selected_words'] = json.dumps(specific_word_ids)
                if specific_word_ids:
                    selected_db_words = Word.query.filter(Word.id.in_(specific_word_ids)).all()
                    for sw in selected_db_words:
                        words_data_source.append({'id': sw.id, 'word': sw.word, 'perevod': sw.perevod, 'source': 'module_specific'})
                new_test_params['word_count'] = word_count_form
            for cw_text, ct_text in zip(custom_words_text, custom_translations_text):
                if cw_text and ct_text:
                    words_data_source.append({'word': cw_text, 'perevod': ct_text, 'source': 'custom'})
        else: 
            new_test_params['word_count'] = word_count_form
            words_data_source.extend(module_words_list)
            for cw_text, ct_text in zip(custom_words_text, custom_translations_text):
                if cw_text and ct_text:
                    words_data_source.append({'word': cw_text, 'perevod': ct_text, 'source': 'custom'})
        
        if len(selected_module_identifiers) == 1:
            try:
                _, unit_single, module_single = selected_module_identifiers[0].split('|')
                new_test_params['unit'] = unit_single
                new_test_params['module'] = module_single
            except ValueError:
                new_test_params['unit'] = "N/A"
                new_test_params['module'] = "N/A"
        elif len(selected_module_identifiers) > 1:
            new_test_params['unit'] = "Multiple"
            new_test_params['module'] = "Multiple"
        else:
            new_test_params['unit'] = "N/A"
            new_test_params['module'] = "N/A"

        if test_type == 'text_based':
            if not text_content or len(text_content.strip()) < 50:
                flash("Для теста по тексту необходимо загрузить текст длиной не менее 50 символов.", "error")
                classes_get = [str(i) for i in range(1, 12)]
                return render_template("add_tests.html", classes=classes_get, **request.form)
            new_test = Test(**new_test_params)
            db.session.add(new_test)
            db.session.commit()
            flash("Тест создан. Теперь добавьте вопросы по загруженному тексту.", "info")
            return redirect(url_for('create_text_based_test', test_id=new_test.id))

        new_test = Test(**new_test_params)
        db.session.add(new_test)
        
        try:
            db.session.commit()
            if new_test.word_order == 'random':
                random.shuffle(words_data_source)
            final_word_count_to_use = new_test.word_count
            if final_word_count_to_use is not None and final_word_count_to_use > 0:
                words_data_source = words_data_source[:final_word_count_to_use]
            elif final_word_count_to_use == 0:
                words_data_source = []

            for idx, word_entry in enumerate(words_data_source):
                original_word_text = word_entry['word']
                original_translation = word_entry['perevod']
                current_word_for_test_word_model = original_word_text 
                prompt_for_test_word_model = original_translation   
                options_db = None
                missing_letters_positions_db = None
                correct_answer_for_db = original_word_text

                # --- Генерация вариантов и ответов для разных типов тестов ---
                if test_type == 'add_letter':
                    prompt_for_test_word_model = original_translation
                    if test_mode == 'random_letters':
                        if len(original_word_text) > 0:
                            num_letters_to_remove = random.randint(1, min(2, len(original_word_text)))
                            positions_zero_indexed = sorted(random.sample(range(len(original_word_text)), num_letters_to_remove))
                            actual_missing_letters_list = [original_word_text[pos] for pos in positions_zero_indexed]
                            correct_answer_for_db = "".join(actual_missing_letters_list)
                            word_with_gaps_list = list(original_word_text)
                            for pos in positions_zero_indexed: word_with_gaps_list[pos] = '_'
                            current_word_for_test_word_model = "".join(word_with_gaps_list)
                            missing_letters_positions_db = ','.join(str(pos + 1) for pos in positions_zero_indexed)
                        else:
                            current_word_for_test_word_model = ""; correct_answer_for_db = ""; missing_letters_positions_db = ""
                    elif test_mode == 'manual_letters':
                        current_word_for_test_word_model = original_word_text
                        correct_answer_for_db = "" 
                        missing_letters_positions_db = None  
                elif test_type == 'multiple_choice':
                    if test_direction == 'word_to_translation':
                        current_word_for_test_word_model = original_word_text
                        prompt_for_test_word_model = "Выберите правильный перевод:"
                        correct_answer_for_db = original_translation
                        all_other_translations = [w.perevod for w in Word.query.filter(Word.classs == class_number, Word.perevod != original_translation).limit(20).all()]
                        num_wrong_options = 3
                        wrong_options_list = random.sample(all_other_translations, min(num_wrong_options, len(all_other_translations)))
                        current_options_list_for_db = wrong_options_list + [original_translation]
                    else:
                        current_word_for_test_word_model = original_translation
                        prompt_for_test_word_model = "Выберите правильное слово:"
                        correct_answer_for_db = original_word_text
                        all_other_words = [w.word for w in Word.query.filter(Word.classs == class_number, Word.word != original_word_text).limit(20).all()]
                        num_wrong_options = 3
                        wrong_options_list = random.sample(all_other_words, min(num_wrong_options, len(all_other_words)))
                        current_options_list_for_db = wrong_options_list + [original_word_text]
                    random.shuffle(current_options_list_for_db)
                    options_db = '|'.join(current_options_list_for_db)
                elif test_type == 'dictation':
                    current_word_for_test_word_model = ''.join(['_'] * len(original_word_text))
                    prompt_for_test_word_model = original_translation 
                    correct_answer_for_db = original_word_text
                elif test_type == 'fill_word':
                    current_word_for_test_word_model = original_translation
                    prompt_for_test_word_model = "Впишите соответствующее слово (оригинал):"
                    correct_answer_for_db = original_word_text

                test_word_entry = TestWord(
                    test_id=new_test.id,
                    word=current_word_for_test_word_model,
                    perevod=prompt_for_test_word_model,
                    correct_answer=correct_answer_for_db,
                    options=options_db,
                    missing_letters=missing_letters_positions_db,
                    word_order=idx
                )
                db.session.add(test_word_entry)
            
            db.session.commit()

            if new_test.type == 'add_letter' and new_test.test_mode == 'manual_letters':
                flash("Тест создан. Теперь укажите, какие буквы пропустить в словах.", "info")
                return redirect(url_for('configure_test_words', test_id=new_test.id))
            else:
                flash("Тест успешно создан!", "success")
                return redirect(url_for('tests'))

        except Exception as e:
            db.session.rollback()
            if new_test.id:
                test_to_delete = db.session.get(Test, new_test.id)
                if test_to_delete:
                    db.session.delete(test_to_delete)
                    db.session.commit()
            flash(f"Ошибка при создании теста или его слов: {str(e)}", "error")
            classes_get = [str(i) for i in range(1, 12)]
            return render_template("add_tests.html", classes=classes_get, error_message=str(e), **request.form)

    else:
        classes = [str(i) for i in range(1, 12)]
        form_data = request.form if request.form else {}
        return render_template("add_tests.html", classes=classes, **form_data)

@app.route("/tests")
def tests():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = db.session.get(User, session['user_id'])
    if not user:
        session.pop('user_id', None)
        flash("Пользователь не найден, пожалуйста, войдите снова.", "error")
        return redirect(url_for('auth.login'))

    show_archived = request.args.get('show_archived', 'false') == 'true'
    
    tests_data = []
    if user.teacher == 'yes':
        # Teachers see all tests they created
        tests_query = Test.query.filter_by(created_by=user.id, is_active=not show_archived).order_by(Test.created_at.desc()).all()
        for test_item in tests_query:
            students_in_class = User.query.filter_by(class_number=test_item.classs, teacher='no').count()
            
            # Corrected logic for completed_results: count only student completions
            completed_count = db.session.query(TestResult.id).join(User, TestResult.user_id == User.id).filter(
                TestResult.test_id == test_item.id,
                TestResult.completed_at.isnot(None),
                User.teacher == 'no',  # Ensure only student results are counted
                TestResult.started_at >= test_item.created_at # New condition
            ).count()

            progress = 0
            if students_in_class > 0:
                progress = round((completed_count / students_in_class) * 100)
            
            # Получаем информацию о тексте для текстовых тестов
            text_content = None
            if test_item.type == 'text_based' and test_item.text_content_id:
                text_content = db.session.get(TextContent, test_item.text_content_id)
            
            tests_data.append({
                'test': test_item,
                'students_in_class': students_in_class,
                'completed_count': completed_count,
                'progress': progress,
                'text_content': text_content
            })
    else:
        # Students see only tests for their class
        tests_query = Test.query.filter_by(classs=user.class_number, is_active=not show_archived).order_by(Test.created_at.desc()).all()
        # For students, we need to check if they completed the test to link to results, especially for archived.
        for test_item in tests_query:
            student_result = TestResult.query.filter_by(
                test_id=test_item.id,
                user_id=user.id,
            ).filter(TestResult.completed_at.isnot(None)).first()

            # Получаем информацию о тексте для текстовых тестов
            text_content = None
            if test_item.type == 'text_based' and test_item.text_content_id:
                text_content = db.session.get(TextContent, test_item.text_content_id)

            tests_data.append({
                'test': test_item,
                'students_in_class': 0, # Not relevant for student's direct view here
                'completed_count': 0, # Not relevant
                'progress': 0, # Not relevant
                'student_completed_result_id': student_result.id if student_result else None,
                'text_content': text_content
            })


    return render_template('tests.html', tests_data=tests_data, show_archived=show_archived, is_teacher=user.teacher == 'yes')

@app.route("/api/tests_progress")
def api_tests_progress():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user = db.session.get(User, session['user_id'])
    if not user or user.teacher != 'yes':
        return jsonify({"error": "Forbidden"}), 403

    # We only care about active tests for live progress updates on the main /tests page
    tests_query = Test.query.filter_by(created_by=user.id, is_active=True).order_by(Test.created_at.desc()).all()
    
    progress_data = []
    for test_item in tests_query:
        students_in_class = User.query.filter_by(class_number=test_item.classs, teacher='no').count()
        
        completed_count = db.session.query(TestResult.id).join(User, TestResult.user_id == User.id).filter(
            TestResult.test_id == test_item.id,
            TestResult.completed_at.isnot(None),
            User.teacher == 'no',
            TestResult.started_at >= test_item.created_at # New condition
        ).count()

        progress_data.append({
            'id': test_item.id,
            'title': test_item.title, # Optional: for debugging or richer display
            'students_in_class': students_in_class,
            'completed_count': completed_count
        })
        
    return jsonify(progress_data)

@app.route("/words/json")
def get_words_json():
    words = Word.query.all()
    data = {}
    for w in words:
        if w.classs not in data:
            data[w.classs] = {}
        if w.unit not in data[w.classs]:
            data[w.classs][w.unit] = []
        data[w.classs][w.unit].append([w.word, w.perevod])
    return jsonify(data)

@app.route("/get_words_for_module_selection")
def get_words_for_module_selection():
    module_identifiers_str = request.args.get('modules', '')
    if not module_identifiers_str:
        return jsonify({"words": [], "error": "No modules provided"})

    module_identifiers = module_identifiers_str.split(',')
    words_list = []
    seen_word_ids = set()

    for module_identifier in module_identifiers:
        parts = module_identifier.split('|')
        if len(parts) == 3:
            class_num, unit_name, module_name = parts
            try:
                module_words_db = Word.query.filter_by(
                    classs=class_num,
                    unit=unit_name,
                    module=module_name
                ).order_by(Word.word).all()
                
                for mw in module_words_db:
                    if mw.id not in seen_word_ids:
                        words_list.append({
                            "id": mw.id,
                            "text": f"{mw.word} - {mw.perevod}" # Format for display
                        })
                        seen_word_ids.add(mw.id)
            except Exception as e:
                # Log error or handle it as needed
                print(f"Error fetching words for module {module_identifier}: {e}") # Basic logging
                # Optionally, you could add an error message to the response for this module
                pass # Continue to next module identifier
        else:
            # Log invalid module identifier
            print(f"Invalid module identifier format: {module_identifier}")
            pass # Continue to next module identifier
            
    return jsonify({"words": words_list})

@app.route('/api/test/<int:test_db_id>/dictation_words', methods=['GET'])
def api_test_dictation_words(test_db_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    user = db.session.get(User, session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 403 # Or 401

    test = db.session.get(Test, test_db_id)
    if not test:
        abort(404)

    if test.type != 'dictation':
        return jsonify({'error': 'Invalid test type for this endpoint'}), 400

    # Teacher preview or student taking test for their class
    if user.teacher != 'yes':
        if test.classs != user.class_number:
            return jsonify({'error': 'Access denied: Test is for a different class'}), 403
        if not test.is_active:
             return jsonify({'error': 'Access denied: Test is not active'}), 403


    test_words_query = TestWord.query.filter_by(test_id=test.id)

    if test.word_order == 'random':
        # Для случайного порядка используем seed на основе user_id и test_id
        # чтобы порядок был одинаковым для одного пользователя и теста
        test_word_objects = list(test_words_query.all()) # Convert to list to shuffle
        
        # Создаем детерминированный seed на основе user_id и test_id
        seed_value = hash(f"{user.id}_{test.id}") % (2**32)
        random.seed(seed_value)
        random.shuffle(test_word_objects)
        random.seed()  # Сбрасываем seed для других операций
    else: # 'sequential' or any other case defaults to ordered
        test_word_objects = test_words_query.order_by(TestWord.word_order).all()

    words_data = []
    for tw in test_word_objects:
        words_data.append({
            'id': tw.id,
            'word_placeholder': tw.word,  # This is the gapped/empty string for dictation display
            'prompt': tw.perevod,         # The translation/hint given to the student
            'correct_answer': tw.correct_answer # The actual word the student needs to type
            # 'options': tw.options, # Not typically used for dictation
            # 'missing_letters': tw.missing_letters # Not typically used for dictation
        })

    return jsonify({'words': words_data, 'test_title': test.title})

# Helper function for fetching test words for various types
def _get_test_words_api_data(test_db_id, expected_test_type_slug):
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    user = db.session.get(User, session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 403

    test = Test.query.get_or_404(test_db_id)

    # Teacher preview or student taking test for their class
    if user.teacher != 'yes':
        if test.classs != user.class_number:
            return jsonify({'error': 'Access denied: Test is for a different class'}), 403
        if not test.is_active:
            return jsonify({'error': 'Access denied: Test is not active'}), 403

    # Validate test type if slug implies a specific type (e.g. multiple_choice for multiple_choice_single)
    db_test_type = test.type
    if expected_test_type_slug == 'multiple_choice_single_words' and db_test_type != 'multiple_choice':
        return jsonify({'error': f'Invalid test type for this endpoint. Expected multiple_choice, got {db_test_type}'}), 400
    elif expected_test_type_slug != 'multiple_choice_single_words' and db_test_type != expected_test_type_slug.replace('_words', ''):
         return jsonify({'error': f'Invalid test type for this endpoint. Expected {expected_test_type_slug.replace("_words", "")}, got {db_test_type}'}), 400


    test_words_query = TestWord.query.filter_by(test_id=test.id)

    if test.word_order == 'random':
        # Для случайного порядка используем seed на основе user_id и test_id
        # чтобы порядок был одинаковым для одного пользователя и теста
        test_word_objects = list(test_words_query.all()) # Convert to list to shuffle
        
        # Создаем детерминированный seed на основе user_id и test_id
        seed_value = hash(f"{user.id}_{test.id}") % (2**32)
        random.seed(seed_value)
        random.shuffle(test_word_objects)
        random.seed()  # Сбрасываем seed для других операций
    else: # 'sequential' or any other case defaults to ordered
        test_word_objects = test_words_query.order_by(TestWord.word_order).all()

    return test, test_word_objects, user


@app.route('/api/test/<int:test_db_id>/add_letter_words', methods=['GET'])
def api_test_add_letter_words(test_db_id):
    result = _get_test_words_api_data(test_db_id, 'add_letter_words')
    if not isinstance(result, tuple): # Error response from helper
        return result
    test, test_word_objects, user = result

    words_data = []
    for tw in test_word_objects:
        words_data.append({
            'id': tw.id,
            'word_gapped': tw.word, # The word with underscores
            'prompt': tw.perevod,   # Translation or hint
            'num_inputs': len(tw.correct_answer) if tw.correct_answer else 0,
            'correct_answer_letters': tw.correct_answer # The actual letters to be filled
        })
    return jsonify({'words': words_data, 'test_title': test.title, 'test_type': test.type, 'test_mode': test.test_mode})

@app.route('/api/test/<int:test_db_id>/true_false_words', methods=['GET'])
def api_test_true_false_words(test_db_id):
    result = _get_test_words_api_data(test_db_id, 'true_false_words')
    if not isinstance(result, tuple):
        return result
    test, test_word_objects, user = result

    words_data = []
    for tw in test_word_objects:
        words_data.append({
            'id': tw.id,
            'statement': tw.word, # The statement to be judged
            'prompt': tw.perevod,  # Usually "Верно или неверно?" or a hint
            'options': tw.options.split('|') if tw.options else ["True", "False", "Not_Stated"], # Include "Not_Stated" option
            'correct_answer': tw.correct_answer # "True", "False", or "Not_Stated"
        })
    return jsonify({'words': words_data, 'test_title': test.title, 'test_type': test.type})

@app.route('/api/test/<int:test_db_id>/multiple_choice_single_words', methods=['GET'])
def api_test_multiple_choice_single_words(test_db_id):
    # Note: DB test.type is 'multiple_choice' for this
    result = _get_test_words_api_data(test_db_id, 'multiple_choice_single_words')
    if not isinstance(result, tuple):
        return result
    test, test_word_objects, user = result

    words_data = []
    for tw in test_word_objects:
        words_data.append({
            'id': tw.id,
            'question': tw.word, # The question text (e.g., word to translate, or definition)
            'prompt': tw.perevod, # Supporting prompt like "Выберите правильный перевод:"
            'options': tw.options.split('|') if tw.options else [],
            'correct_answer': tw.correct_answer
        })
    return jsonify({'words': words_data, 'test_title': test.title, 'test_type': test.type})


@app.route('/api/test/<int:test_db_id>/fill_word_words', methods=['GET'])
def api_test_fill_word_words(test_db_id):
    result = _get_test_words_api_data(test_db_id, 'fill_word_words')
    if not isinstance(result, tuple):
        return result
    test, test_word_objects, user = result

    words_data = []
    for tw in test_word_objects:
        words_data.append({
            'id': tw.id,
            'question_prompt': tw.word, # The prompt, e.g., a sentence with a blank or a definition
            'instruction': tw.perevod, # Specific instruction like "Впишите слово"
            'correct_answer': tw.correct_answer
        })
    return jsonify({'words': words_data, 'test_title': test.title, 'test_type': test.type})

@app.route('/api/test/<int:test_db_id>/multiple_choice_multiple_words', methods=['GET'])
def api_test_multiple_choice_multiple_words(test_db_id):
    result = _get_test_words_api_data(test_db_id, 'multiple_choice_multiple_words')
    if not isinstance(result, tuple):
        return result
    test, test_word_objects, user = result

    words_data = []
    for tw in test_word_objects:
        words_data.append({
            'id': tw.id,
            'question': tw.word, # The question or statement
            'prompt': tw.perevod, # Supporting prompt like "Выберите все подходящие варианты:"
            'options': tw.options.split('|') if tw.options else [],
            'correct_answers_pipe_separated': tw.correct_answer # Correct answers, e.g. "ans1|ans3"
        })
    return jsonify({'words': words_data, 'test_title': test.title, 'test_type': test.type})

@app.route("/test/<id>", methods=['GET', 'POST'])
def test_id(id):
    if 'user_id' not in session:
        flash("Пожалуйста, войдите в систему, чтобы пройти тест.", "error")
        return redirect(url_for('auth.login'))

    user = db.session.get(User, session['user_id'])
    if not user:
        session.pop('user_id', None)
        flash("Пользователь не найден, пожалуйста, войдите снова.", "error")
        return redirect(url_for('auth.login'))
        
    # Отладочная информация о сессии и cookies
    print(f"DEBUG: test_id route - session data: {dict(session)}")
    print(f"DEBUG: Current user: {user.nick}, ID: {user.id}")
    print(f"DEBUG: Cookies: {request.cookies}")
    
    if 'active_test_result_id' in session:
        print(f"DEBUG: active_test_result_id from session: {session['active_test_result_id']}")
    else:
        print("DEBUG: No active_test_result_id in session")
        
    if 'active_test_result_id' in request.cookies:
        print(f"DEBUG: active_test_result_id from cookie: {request.cookies.get('active_test_result_id')}")

    test = Test.query.filter_by(link=id).first()
    if not test:
        abort(404)

    # Проверяем, является ли это режимом предпросмотра для учителя
    is_teacher_preview_mode = False
    if user.teacher == 'yes' and (session.get('is_teacher_preview', False) or session.get('test_link') == id):
        is_teacher_preview_mode = True
        print("DEBUG: Teacher preview mode detected")
    
    # Получаем активный тест из сессии или cookie для студента
    test_result = None
    
    # Для учителей в режиме предпросмотра test_result остается None
    if not is_teacher_preview_mode:
        # Сначала пробуем получить из сессии
        if 'active_test_result_id' in session:
            test_result_id = session['active_test_result_id']
            test_result = db.session.get(TestResult, test_result_id)
            print(f"DEBUG: Found test_result from session: {test_result}")
        
        # Если не нашли в сессии, пробуем из cookie
        if not test_result and 'active_test_result_id' in request.cookies:
            try:
                test_result_id = int(request.cookies.get('active_test_result_id'))
                test_result = db.session.get(TestResult, test_result_id)
                if test_result:
                    # Если нашли в cookie, сохраняем в сессию для будущих запросов
                    session['active_test_result_id'] = test_result_id
                    session['test_link'] = id
                    session.modified = True
                    print(f"DEBUG: Found test_result from cookie and saved to session: {test_result}")
            except (ValueError, TypeError):
                print("DEBUG: Invalid test_result_id in cookie")
    
    # Если пользователь не учитель и нет активного теста ни в сессии, ни в cookie,
    # пробуем найти незавершенный тест для этого пользователя и этого теста
    if user.teacher == 'no' and not test_result:
        incomplete_result = TestResult.query.filter_by(
            test_id=test.id,
            user_id=user.id,
            completed_at=None
        ).first()
        
        if incomplete_result:
            test_result = incomplete_result
            session['active_test_result_id'] = incomplete_result.id
            session['test_link'] = id
            session.modified = True
            print(f"DEBUG: Found incomplete test result from database: {test_result}")
        else:
            print("DEBUG: Student without active test result, redirecting to take_test")
            flash("Пожалуйста, начните тест с начальной страницы.", "warning")
            return redirect(url_for('take_test', test_link=id))

    # Handle POST requests (submitting answers)
    if request.method == 'POST':
        if user.teacher == 'yes':
            # Teachers in preview mode do not save results
            flash("Предпросмотр теста. Ответы не были сохранены.", "info")
            return redirect(url_for('test_details', test_id=test.id))
        
        # --- STUDENT SUBMISSION LOGIC (remains largely the same) ---
        if not test_result: # Should not happen if student started test correctly
            # This indicates a potential issue or direct POST without GET,
            # or test_result was not initiated properly.
            # For robustness, try to get or create one.
            test_result = TestResult.query.filter_by(
                test_id=test.id,
                user_id=user.id,
                completed_at=None
            ).first()
            if not test_result: # If still not found, student likely hasn't started.
                                # This situation ideally is caught by GET request flow.
                flash("Не удалось найти активный сеанс теста. Пожалуйста, начните тест сначала.", "warning")
                return redirect(url_for('take_test', test_link=test.link)) # Redirect to start

        # Process answers based on test type
        if test.type == 'text_based':
            # Обработка текстовых тестов
            # Получаем вопросы - сначала пробуем новую структуру
            questions = []
            if test.text_content_id:
                # Используем новую структуру с TextQuestion
                text_questions = db.session.execute(
                    db.select(TextQuestion).where(
                        TextQuestion.text_content_id == test.text_content_id
                    ).order_by(TextQuestion.order_number)
                ).scalars().all()
                
                questions = text_questions
            elif test.text_based_questions:
                # Fallback к старой структуре
                try:
                    old_questions = json.loads(test.text_based_questions)
                    # Преобразуем в объекты для совместимости
                    questions = []
                    for i, q in enumerate(old_questions):
                        class OldQuestion:
                            def __init__(self, data, index):
                                self.id = f"old_{index}"
                                self.question = data.get('question', '')
                                self.question_type = data.get('type', 'open_answer')
                                self.correct_answer = data.get('correct', '')
                                self.points = 1
                                self.options = data.get('options', [])
                        questions.append(OldQuestion(q, i))
                except json.JSONDecodeError:
                    questions = []
            
            # Получение ответов из формы и подсчет правильных ответов
            correct_count = 0
            total_points = 0
            earned_points = 0
            
            for i, question in enumerate(questions):
                question_key = f'question_{i}'
                user_answer = request.form.get(question_key, '').strip()
                
                # Проверка правильности ответа
                is_correct = False
                points_for_question = getattr(question, 'points', 1)
                total_points += points_for_question
                
                if question.question_type == 'multiple_choice':
                    is_correct = user_answer == question.correct_answer
                elif question.question_type == 'multiple_select':
                    # Для множественного выбора сравниваем JSON массивы
                    try:
                        user_answers = json.loads(user_answer) if user_answer else []
                        correct_answers = json.loads(question.correct_answer) if question.correct_answer else []
                        # Сравниваем отсортированные списки для корректного сравнения
                        is_correct = sorted(user_answers) == sorted(correct_answers)
                    except json.JSONDecodeError:
                        is_correct = False
                elif question.question_type == 'true_false':
                    # Поддержка "Да", "Нет", "Не указано"
                    is_correct = user_answer == question.correct_answer
                elif question.question_type == 'open_answer':
                    # Для открытых вопросов проверяем точное совпадение (можно улучшить)
                    is_correct = user_answer.lower().strip() == question.correct_answer.lower().strip()
                
                if is_correct:
                    correct_count += 1
                    earned_points += points_for_question
                
                # Сохраняем ответ в новой структуре, если используем TextQuestion
                if hasattr(question, 'id') and isinstance(question.id, int):
                    text_answer = TextTestAnswer(
                        test_result_id=test_result.id,
                        text_question_id=question.id,
                        user_answer=user_answer,
                        is_correct=is_correct,
                        points_earned=points_for_question if is_correct else 0
                    )
                    db.session.add(text_answer)
            
            # Обновление результата теста
            test_result.correct_answers = correct_count
            test_result.score = int((earned_points / total_points) * 100) if total_points > 0 else 0
            completion_time = datetime.utcnow()
            test_result.completed_at = completion_time
            
            # Вычисляем время выполнения
            if test_result.started_at:
                time_diff = completion_time - test_result.started_at
                test_result.time_taken = max(0, int(time_diff.total_seconds() / 60))
            else:
                test_result.time_taken = 0
            
            db.session.commit()
            
            return redirect(url_for('view_text_test_result', test_result_id=test_result.id))
        
        # Process answers for word-based tests
        answers_dict_for_json = {} # To store in TestResult.answers (JSON)
        score = 0
        processed_answers_for_db = [] # To store TestAnswer objects

        for word in test.test_words:
            user_input_answer = request.form.get(f'answer{word.id}', '').strip()
            # Storing raw user input for TestAnswer, lowercasing for comparison
            user_answer_for_comparison = user_input_answer.lower()
            
            answers_dict_for_json[str(word.id)] = user_input_answer # Store original case for JSON

            is_this_answer_correct = False
            actual_correct_answer_for_comparison = word.correct_answer.lower()

            if test.type == 'add_letter':
                # For add_letter, word.correct_answer already holds the combined missing letters
                if user_answer_for_comparison == actual_correct_answer_for_comparison:
                    is_this_answer_correct = True
            elif test.type == 'multiple_choice_single' or test.type == 'multiple_choice_multiple':
                # For MC, word.correct_answer holds the correct option text
                if user_answer_for_comparison == actual_correct_answer_for_comparison:
                    is_this_answer_correct = True
            elif test.type == 'dictation':
                if user_answer_for_comparison == actual_correct_answer_for_comparison:
                    is_this_answer_correct = True
            elif test.type == 'true_false':
                # For true_false, correct_answer is 'True', 'False', or 'Not_Stated'
                if user_input_answer == word.correct_answer: # Direct comparison for T/F/NS
                    is_this_answer_correct = True
            elif test.type == 'fill_word':
                if user_answer_for_comparison == actual_correct_answer_for_comparison:
                    is_this_answer_correct = True
            else: # Fallback for any other types or if logic is missing
                if user_answer_for_comparison == actual_correct_answer_for_comparison:
                    is_this_answer_correct = True
            
            if is_this_answer_correct:
                score += 1
            
            processed_answers_for_db.append({
                'test_word_id': word.id,
                'user_answer': user_input_answer, # Store raw input
                'is_correct': is_this_answer_correct
            })

        # Update test result
        test_result.score = int((score / len(test.test_words)) * 100) if len(test.test_words) > 0 else 0
        test_result.correct_answers = score
        completion_time = datetime.utcnow()
        test_result.completed_at = completion_time
        
        # Calculate time taken in minutes (safe calculation)
        if test_result.started_at:
            time_diff = completion_time - test_result.started_at
            test_result.time_taken = max(0, int(time_diff.total_seconds() / 60))  # Convert to minutes, ensure non-negative
        else:
            test_result.time_taken = 0  # Fallback if started_at is missing
            
        test_result.answers = json.dumps(answers_dict_for_json) # Keep the JSON dump as it might be used elsewhere or for quick view
        
        # Add TestAnswer instances
        for ans_data in processed_answers_for_db:
            test_answer_entry = TestAnswer(
                test_result_id=test_result.id,
                test_word_id=ans_data['test_word_id'],
                user_answer=ans_data['user_answer'],
                is_correct=ans_data['is_correct']
            )
            db.session.add(test_answer_entry)

        db.session.commit()

        return redirect(url_for('test_results', test_id=test.id, result_id=test_result.id))

    # --- HANDLE GET REQUESTS ---

    # Teacher Preview Logic for GET
    if user.teacher == 'yes':
        # Teachers can preview their own tests or any active test.
        # If archived, only creator can preview.
        if not test.is_active and test.created_by != user.id:
            flash("Этот тест заархивирован, и вы не являетесь его создателем. Предпросмотр невозможен.", "warning")
            return redirect(url_for('tests'))
        
        is_teacher_preview_mode = True
        # For teachers, no TestResult is needed for preview.
        # Time is unlimited for preview.
        remaining_time_seconds = -1 # Indicator for unlimited time
        test_result = None # Explicitly set to None for teacher preview context
    
    # Student Test-Taking Logic for GET
    else: # user.teacher == 'no'
        # Check if student has access to this test (class matches)
        print(f"DEBUG: test.classs={test.classs}, user.class_number={user.class_number}")
        if test.classs != user.class_number:
            flash(f"Доступ запрещен: тест предназначен для класса {test.classs}, а вы в классе {user.class_number}.", "error")
            return redirect(url_for('tests'))

        # Check if test is active (students cannot take archived tests)
        if not test.is_active:
            flash("Этот тест больше не активен.", "error")
            return redirect(url_for('tests'))

        # Get or create test result for students
        test_result = TestResult.query.filter_by(
            test_id=test.id,
            user_id=user.id,
            completed_at=None
        ).first()

        if test_result: # An incomplete test was found
            if not test_result.started_at: # Ensure it has a start time if resuming
                test_result.started_at = datetime.utcnow()
                db.session.commit()
        else: # No incomplete test_result was found
            completed_test_run = TestResult.query.filter_by(
                test_id=test.id,
                user_id=user.id
            ).filter(TestResult.completed_at.isnot(None)).order_by(TestResult.completed_at.desc()).first()

            if completed_test_run:
                flash("Вы уже завершили этот тест. Просмотр ваших результатов.", "info")
                return redirect(url_for('test_results', test_id=test.id, result_id=completed_test_run.id))
            else:
                # Student is starting for the first time
                test_result = TestResult(
                    test_id=test.id,
                    user_id=user.id,
                    total_questions=len(test.test_words) if test.test_words else 0,
                    started_at=datetime.utcnow()
                )
                db.session.add(test_result)
                db.session.commit()
        
        # Calculate remaining time for students
        remaining_time_seconds = -1 # Default for unlimited time
        time_is_up_on_server = False
        if test.time_limit and test.time_limit > 0 and test_result and test_result.started_at:
            elapsed_seconds = (datetime.utcnow() - test_result.started_at).total_seconds()
            total_duration_seconds = test.time_limit * 60
            remaining_time_seconds = max(0, int(total_duration_seconds - elapsed_seconds))
            if remaining_time_seconds == 0:
                time_is_up_on_server = True
                if not test_result.completed_at: # Auto-submit if time is up on server
                    flash("Время на тест вышло. Тест будет отправлен автоматически.", "warning")
                    # Simplified auto-submit: mark as completed. Client should ideally handle submission.
                    # For a more robust auto-submit, answers would need to be saved progressively.
                    # Consider if answers submitted via form post-timeout should be accepted or rejected.
                    # The POST handler has its own time check.
                    pass # Let client-side timer trigger submission for now.


    # Common rendering logic for both teachers (preview) and students (taking test)
    # The specific template and words_list will depend on test.type

    if test.type == 'add_letter':
        if not is_teacher_preview_mode: # Student specific checks
            if test.test_mode == 'manual_letters':
                if test.test_words and any(tw.missing_letters is None for tw in test.test_words):
                    flash("Этот тест (вставить буквы) еще не полностью настроен учителем и пока не доступен для прохождения.", "warning")
                    return redirect(url_for('tests'))

        # words_list = []
        # for word in test.test_words:
            # Debug prints can be removed in production
            # print(f"--- Word Details for Test '{test.title}' (Link: {test.link}) ---")
            # print(f"  TestWord ID: {word.id}")
            # print(f"  Gapped Word (to display): '{word.word}'")
            # print(f"  Translation/Hint: '{word.perevod}'")
            # print(f"  Correct letters (to be inserted by student): '{word.correct_answer}'")
            # if word.missing_letters:
            #     print(f"  Missing letter positions (1-indexed in original word): '{word.missing_letters}'")
            # print(f"  Number of letters to input: {len(word.correct_answer) if word.correct_answer else 0}")
            # print("-" * 40)
            # words_list.append({
            #     'id': word.id,
            #     'word': word.word,
            #     'perevod': word.perevod,
            #     'num_inputs': len(word.correct_answer) if word.correct_answer else 0
            # })
        return render_template('test_add_letter.html', 
                             # words=words_list,
                             test_id=id, # link
                             test_result=test_result, # Will be None for teacher preview
                             time_limit=test.time_limit,
                             remaining_time_seconds=remaining_time_seconds,
                             test_title=test.title, 
                             test_db_id=test.id, # numerical ID
                             is_teacher_preview=is_teacher_preview_mode) # Pass the preview flag
    elif test.type == 'dictation':
        # This block was modified in the previous step, ensuring it remains correct.
        # Debug prints can be removed
        # print(f"DEBUG: Accessing dictation test with link: {id}")
        # print(f"DEBUG: Test object: {test}")
        # print(f"DEBUG: Test.test_words count: {len(test.test_words) if test.test_words else 0}")
        # if test.test_words:
        #     for i, tw in enumerate(test.test_words):
        #         print(f"DEBUG: TestWord {i}: id={tw.id}, word='{tw.word}', perevod='{tw.perevod}', correct_answer='{tw.correct_answer}'")
        
        # words_list = [(word.word, word.perevod, word.correct_answer, word.id) for word in test.test_words]
        
        current_test_result_for_template = test_result # Use the one determined by student/teacher logic
        if is_teacher_preview_mode:
            current_test_result_for_template = None # Ensure no result object for teacher preview

        return render_template('test_dictation.html', 
                             test_title=test.title,
                             # words_data=words_list, # Removed as per requirement
                             test_link_id=id,
                             current_test_result=current_test_result_for_template, # Pass the correct result object
                             time_limit_seconds=test.time_limit * 60 if test.time_limit else 0,
                             remaining_time_seconds=remaining_time_seconds,
                             test_db_id=test.id,
                             is_teacher_preview=is_teacher_preview_mode) # Pass the preview flag
    elif test.type == 'true_false':
        # words_list = [(word.word, word.perevod, word.id) for word in test.test_words] # Added word.id
        return render_template('test_true_false.html',
                             # words=words_list,
                             test_id=id, # link
                             test_result=test_result, # Will be None for teacher preview
                             time_limit=test.time_limit,
                             remaining_time_seconds=remaining_time_seconds,
                             test_title=test.title,
                             test_db_id=test.id,
                             is_teacher_preview=is_teacher_preview_mode)
    elif test.type == 'multiple_choice':
        # words_list = []
        # for word in test.test_words:
            # options = word.options.split('|') if word.options else []
            # words_list.append({
                # 'id': word.id,
                # 'word': word.word, # This is the question (e.g., translation)
                # 'perevod': word.perevod, # This is the prompt (e.g., "Choose the correct word")
                # 'options': options
            # })
        return render_template('test_multiple_choice.html', 
                             # words=words_list,
                             test_id=id, # link
                             test_result=test_result, # Will be None for teacher preview
                             time_limit=test.time_limit,
                             remaining_time_seconds=remaining_time_seconds,
                             test_title=test.title,
                             test_db_id=test.id,
                             is_teacher_preview=is_teacher_preview_mode)
    elif test.type == 'fill_word':
        # words_list = []
        # for word in test.test_words:
            # words_list.append({
                # 'id': word.id,
                # 'word': word.word, # This is the question (e.g., translation)
                # 'perevod': word.perevod # This is the prompt (e.g., "Fill in the original word")
            # })
        return render_template('test_fill_word.html',
                             # words=words_list,
                             test_id=id, # link
                             test_result=test_result, # Will be None for teacher preview
                             time_limit=test.time_limit,
                             remaining_time_seconds=remaining_time_seconds,
                             test_title=test.title,
                             test_db_id=test.id,
                             is_teacher_preview=is_teacher_preview_mode)
    elif test.type == 'multiple_choice_multiple':
        # words_list = []
        # for word in test.test_words:
            # options = word.options.split('|') if word.options else []
            # words_list.append({
                # 'id': word.id,
                # 'word': word.word,       # Question (e.g., translation/definition)
                # 'perevod': word.perevod, # Prompt (e.g., "Select all correct options")
                # 'options': options
            # })
        return render_template('test_multiple_choice_multiple.html',
                             # words=words_list,
                             test_id=id, # link
                             test_result=test_result, # Will be None for teacher preview
                             time_limit=test.time_limit,
                             remaining_time_seconds=remaining_time_seconds,
                             test_title=test.title,
                             test_db_id=test.id,
                             is_teacher_preview=is_teacher_preview_mode)
    elif test.type == 'text_based':
        # Обработка текстовых тестов
        # Проверка наличия вопросов - сначала пробуем новую структуру
        questions = []
        if test.text_content_id:
            # Используем новую структуру с TextQuestion
            text_questions = db.session.execute(
                db.select(TextQuestion).where(
                    TextQuestion.text_content_id == test.text_content_id
                ).order_by(TextQuestion.order_number)
            ).scalars().all()
            
            questions = []
            for tq in text_questions:
                question_data = {
                    'id': tq.id,
                    'question': tq.question,
                    'type': tq.question_type,
                    'correct_answer': tq.correct_answer,
                    'points': tq.points
                }
                if tq.options:
                    try:
                        question_data['options'] = json.loads(tq.options)
                    except json.JSONDecodeError:
                        question_data['options'] = []
                questions.append(question_data)
        elif test.text_based_questions:
            # Fallback к старой структуре
            try:
                questions = json.loads(test.text_based_questions)
            except json.JSONDecodeError:
                questions = []
        
        if not questions:
            flash('В тесте нет вопросов', 'error')
            return redirect(url_for('tests'))
        
        # Получаем текстовый контент
        text_content = None
        if test.text_content_id:
            text_content = db.session.get(TextContent, test.text_content_id)
        
        return render_template('take_text_test.html', 
                             test=test, 
                             questions=questions,
                             test_result=test_result,
                             text_content=text_content,
                             test_id=id, # link
                             time_limit=test.time_limit,
                             remaining_time_seconds=remaining_time_seconds,
                             test_title=test.title,
                             test_db_id=test.id,
                             is_teacher_preview=is_teacher_preview_mode)
    else:
        # Fallback for unknown test types
        flash(f"Неизвестный тип теста: {test.type}", "error")
        return redirect(url_for('tests'))

@app.route("/edit_profile")
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = db.session.get(User, session['user_id'])
    if not user:
        session.pop('user_id', None)
        flash("Пользователь не найден, пожалуйста, войдите снова.", "error")
        return redirect(url_for('auth.login'))
        
    return render_template('edit_profile.html', nick=user.nick, fio=user.fio)

@app.route("/save_profile", methods=["POST"])
def save_profile():
    fio = request.form.get("fio")
    nick = request.form.get("nick")

    user = User.query.filter_by(nick=nick).first()
    if user:
        user.fio = fio
        db.session.commit()

    return redirect("/profile")

# @app.route("/add_words", methods=['POST', 'GET']) # This route is now handled by words_bp
# def add_words():
#     ... (implementation removed) ...

@app.route("/test_dropdowns")
def test_dropdowns():
    return send_from_directory('.', 'test_dropdowns.html')

@app.route("/get_units_for_class")
def get_units_for_class():
    class_name = request.args.get('class_name')
    if not class_name:
        return jsonify([])
    
    # Get unique units for the selected class
    units = db.session.query(Word.unit).filter(
        Word.classs == class_name,
        Word.unit.isnot(None),
        Word.unit != ''
    ).distinct().all()
    
    return jsonify([unit[0] for unit in units if unit[0]])

@app.route("/get_modules_for_unit")
def get_modules_for_unit():
    class_name = request.args.get('class_name')
    unit_name = request.args.get('unit_name')
    
    if not class_name or not unit_name:
        return jsonify([])
    
    # Get unique modules for the selected class and unit
    modules = db.session.query(Word.module).filter(
        Word.classs == class_name,
        Word.unit == unit_name,
        Word.module.isnot(None),
        Word.module != ''
    ).distinct().all()
    
    return jsonify([module[0] for module in modules if module[0]])

@app.route('/get_word_count')
def get_word_count():
    class_name = request.args.get('class_name')
    unit_name = request.args.get('unit_name')
    module_name = request.args.get('module_name')
    units = request.args.getlist('units')
    modules = request.args.getlist('modules')
    
    if not class_name:
        return jsonify({'count': 0})
    
    query = Word.query.filter_by(classs=class_name)
    
    if units:
        # Multiple units
        query = query.filter(Word.unit.in_(units))
    elif unit_name:
        query = query.filter_by(unit=unit_name)
        
        if modules:
            # Multiple modules within a unit
            query = query.filter(Word.module.in_(modules))
        elif module_name:
            # Specific module
            query = query.filter_by(module=module_name)
    
    count = query.count()
    return jsonify({'count': count})

@app.route("/get_modules_for_sentence_game")
def get_modules_for_sentence_game():
    class_name = request.args.get('class_name')
    unit_name = request.args.get('unit_name')
    
    if not class_name or not unit_name:
        return jsonify([])
    
    # Get unique modules for the selected class and unit that have sentences
    modules = db.session.query(Sentence.module).filter(
        Sentence.classs == class_name,
        Sentence.unit == unit_name
    ).distinct().order_by(Sentence.module).all()
    
    return jsonify([module[0] for module in modules if module[0]])

# Words routes are now in blueprints.words
# @app.route('/words/json') ... (moved)
# @app.route("/get_units_for_class") ... (moved)
# @app.route("/get_modules_for_unit") ... (moved)
# @app.route('/words') ... (moved)
# @app.route("/add_words", methods=['POST', 'GET']) ... (moved)
# @app.route('/edit_word/<int:word_id>', methods=['GET', 'POST']) ... (moved)
# @app.route('/delete_word/<int:word_id>', methods=['POST']) ... (moved)
# @app.route('/class/<class_name>/<unit_name>/<module_name>') ... (moved)
# @app.route('/quizlet/<class_name>/<unit_name>/<module_name>') ... (moved)
# Note: Obsolete /edit_word and /update_word routes were already removed or not part of this list.
# Note: Granular add routes like /add_unit_to_class were already removed or not part of this list.


@app.route("/hello")
def hello():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = db.session.get(User, session['user_id'])
    if not user:
        session.pop('user_id', None) # Clean up invalid session
        flash("Пользователь не найден, пожалуйста, войдите снова.", "error")
        return redirect(url_for('auth.login'))

    fio_parts = user.fio.split(' ')
    try:
        letters = fio_parts[0][:1] + fio_parts[1][:1]
    except:
        letters = user.fio[0] + user.fio[1]

    return render_template('hello.html', username=user.nick, letters=letters)

@app.route("/about")
def about():
    return render_template("about.html")

# Old delete_word route removed in favor of the new route with more precise word identification

# @app.route("/edit_word") # This route is now handled by words_bp.edit_word
# def edit_word_form():
#  ... (implementation removed) ...

# @app.route("/update_word", methods=["POST"]) # This functionality is now part of words_bp.edit_word (POST)
# def update_word():
#  ... (implementation removed) ...

@app.route("/add_unit_to_class")
def add_unit_to_class_form():
    class_name = request.args.get("class")
    return f"""
    <h2>Добавить юнит в {class_name}</h2>
    <form action="/save_unit" method="POST">
        <input type="hidden" name="class" value="{class_name}" />
        <input type="text" name="unit" placeholder="Название юнита" required />
        <button type="submit">Сохранить</button>
    </form>
    """
@app.route("/add_module_to_unit")
def add_module_to_unit_form():
    class_name = request.args.get("class")
    unit_name = request.args.get("unit")
    return f"""
    <h2>Добавить модуль в {unit_name} ({class_name})</h2>
    <form action="/save_module" method="POST">
        <input type="hidden" name="class" value="{class_name}" />
        <input type="hidden" name="unit" value="{unit_name}" />
        <input type="text" name="module" placeholder="Название модуля" required />
        <button type="submit">Сохранить</button>
    </form>
    """

@app.route("/save_module", methods=["POST"])
def save_module():
    class_name = request.form.get("class")
    unit_name = request.form.get("unit")
    module_name = request.form.get("module")

    dummy_word = Word(word="dummy", perevod="заглушка", classs=class_name, unit=unit_name, module=module_name)
    db.session.add(dummy_word)
    db.session.commit()

    return redirect(url_for('words.words'))

@app.route("/add_word_to_module")
def add_word_to_module_form():
    class_name = request.args.get("class")
    unit_name = request.args.get("unit")
    module_name = request.args.get("module")
    return f"""
    <h2>Добавить слово в модуль: {module_name} ({unit_name}, {class_name})</h2>
    <form action="/add_word" method="POST">
        <input type="hidden" name="class" value="{class_name}" />
        <input type="hidden" name="unit" value="{unit_name}" />
        <input type="hidden" name="module" value="{module_name}" />
        <label>Слово:</label><br/>
        <input type="text" name="word" required /><br/>
        <label>Перевод:</label><br/>
        <input type="text" name="perevod" required /><br/>
        <button type="submit">Добавить</button>
    </form>
    """

@app.route("/save_unit", methods=["POST"])
def save_unit():
    class_name = request.form.get("class")
    unit_name = request.form.get("unit")

    # Просто добавляем любое слово, чтобы создать связь класса и модуля
    dummy_word = Word(word="dummy", perevod="заглушка", classs=class_name, unit=unit_name)
    db.session.add(dummy_word)
    db.session.commit()

    return redirect(url_for('words.words'))

@app.route("/add_word_to_unit")
def add_word_to_unit_form():
    class_name = request.args.get("class")
    unit_name = request.args.get("unit")
    return f"""
    <h2>Добавить слово в {unit_name} ({class_name})</h2>
    <form action="/add_word" method="POST">
        <input type="hidden" name="class" value="{class_name}" />
        <input type="hidden" name="unit" value="{unit_name}" />
        <label>Слово:</label><br/>
        <input type="text" name="word" required /><br/>
        <label>Перевод:</label><br/>
        <input type="text" name="perevod" required /><br/>
        <button type="submit">Добавить</button>
    </form>
    """

@app.route("/add_word", methods=["POST"])
def add_word():
    class_name = request.form.get("class")
    unit_name = request.form.get("unit")
    module_name = request.form.get("module")
    word = request.form.get("word")
    perevod = request.form.get("perevod")

    # Validate that all required fields are filled out
    if not class_name or not unit_name or not module_name:
        flash("Невозможно добавить слово: необходимо заполнить класс, юнит и модуль", "error")
        return redirect(url_for('words.words'))

    new_word = Word(word=word, perevod=perevod, classs=class_name, unit=unit_name, module=module_name)
    db.session.add(new_word)
    db.session.commit()

    return redirect(url_for('words.words'))



@app.route('/class/<class_name>/<unit_name>/<module_name>')
def module_words(class_name, unit_name, module_name):
    words = Word.query.filter_by(classs=class_name, unit=unit_name, module=module_name).all()
    return render_template('module_words.html', 
                         words=words,
                         class_name=class_name,
                         unit_name=unit_name,
                         module_name=module_name)

@app.route('/quizlet/<class_name>/<unit_name>/<module_name>')
def quizlet_cards(class_name, unit_name, module_name):
    word_objects = Word.query.filter_by(classs=class_name, unit=unit_name, module=module_name).all()
    # Convert Word objects to dictionaries for JSON serialization
    words = [{'id': word.id, 'word': word.word, 'perevod': word.perevod, 
              'classs': word.classs, 'unit': word.unit, 'module': word.module} 
             for word in word_objects]
    return render_template('quizlet_cards.html',
                         words=words,
                         class_name=class_name,
                         unit_name=unit_name,
                         module_name=module_name)

def generate_test_link():
    """Generate a random unique link for a test"""
    while True:
        link = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        if not Test.query.filter_by(link=link).first():
            return link

@app.route("/create_test", methods=['GET', 'POST'])
def create_test():
    if 'user_id' not in session:
        flash("Доступ запрещен. Пожалуйста, войдите как учитель.", "warning")
        return redirect(url_for('auth.login'))

    user = db.session.get(User, session['user_id'])
    if not user or user.teacher != 'yes':
        flash("Доступ запрещен. Только учителя могут создавать тесты.", "warning")
        if not user: # If user is None (e.g. ID in session is invalid), pop session and redirect
            session.pop('user_id', None)
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        test_type = request.form.get('test_type')
        class_number = request.form.get('class_number')
        title = request.form.get('title')
        
        time_limit_str = request.form.get('time_limit')
        # Time limit: 0 or empty means None (unlimited)
        time_limit = int(time_limit_str) if time_limit_str and time_limit_str.isdigit() and int(time_limit_str) > 0 else None
        
        # General word order for the final list of test words
        word_order_form = request.form.get('word_order', 'sequential') 
        
        # General word count to limit the final number of words (can be None)
        word_count_form_str = request.form.get('word_count')
        word_count_form = int(word_count_form_str) if word_count_form_str and word_count_form_str.isdigit() and int(word_count_form_str) > 0 else None

        test_mode = request.form.get('test_mode', 'random_letters') if test_type == 'add_letter' else None
        
        new_test_params = {
            'title': title,
            'classs': class_number,
            'type': test_type,
            'link': generate_test_link(),
            'created_by': user.id,
            'time_limit': time_limit,
            'word_order': word_order_form, # This is the overall order
            'test_mode': test_mode,
            # unit and module will default to "N/A" if not provided by selected modules
        }

        words_data_source = [] # Holds {'word': ..., 'perevod': ..., 'source': ...}

        if test_type == 'dictation':
            dictation_word_source = request.form.get('dictation_word_source')
            new_test_params['dictation_word_source'] = dictation_word_source

            selected_modules = request.form.getlist('modules[]')
            module_words_list = []
            if selected_modules: # Fetch module words if any modules are selected
                for module_identifier in selected_modules:
                    class_num, unit, module_name = module_identifier.split('|')
                    module_words_db = Word.query.filter_by(
                        classs=class_num,
                        unit=unit,
                        module=module_name
                    ).all()
                    for mw in module_words_db:
                        module_words_list.append({'word': mw.word, 'perevod': mw.perevod, 'source': 'module'})
            
            if dictation_word_source == 'all_module':
                words_data_source.extend(module_words_list)
                # General word_count_form applies as a limiter
                new_test_params['word_count'] = word_count_form 

            elif dictation_word_source == 'random_from_module':
                dictation_num_random_words_str = request.form.get('dictation_random_word_count')
                dictation_num_random_words = int(dictation_num_random_words_str) if dictation_num_random_words_str and dictation_num_random_words_str.isdigit() else 0
                
                new_test_params['word_count'] = dictation_num_random_words if dictation_num_random_words > 0 else None # Store the count of random words
                
                if module_words_list and dictation_num_random_words > 0:
                    random.shuffle(module_words_list)
                    words_data_source.extend(module_words_list[:dictation_num_random_words])

            elif dictation_word_source == 'selected_specific':
                specific_word_ids_str = request.form.getlist('dictation_specific_word_ids[]')
                specific_word_ids = [int(id_str) for id_str in specific_word_ids_str if id_str.isdigit()]
                new_test_params['dictation_selected_words'] = json.dumps(specific_word_ids)
                
                if specific_word_ids:
                    selected_db_words = Word.query.filter(Word.id.in_(specific_word_ids)).all()
                    for sw in selected_db_words:
                        words_data_source.append({'word': sw.word, 'perevod': sw.perevod, 'source': 'module_specific'})
                # General word_count_form can optionally limit these selected words
                new_test_params['word_count'] = word_count_form

            # Add custom words for dictation - these are always included
            custom_words_text = request.form.getlist('custom_words[]')
            custom_translations_text = request.form.getlist('custom_translations[]')
            for cw_text, ct_text in zip(custom_words_text, custom_translations_text):
                if cw_text and ct_text:
                    words_data_source.append({'word': cw_text, 'perevod': ct_text, 'source': 'custom'})
        
        else: # For other test types (non-dictation)
            new_test_params['word_count'] = word_count_form # General word count applies

            selected_modules = request.form.getlist('modules[]')
            if selected_modules:
                for module_identifier in selected_modules:
                    class_num, unit, module_name = module_identifier.split('|')
                    module_words_db = Word.query.filter_by(
                        classs=class_num,
                        unit=unit,
                        module=module_name
                    ).all()
                    for mw in module_words_db:
                        words_data_source.append({'word': mw.word, 'perevod': mw.perevod, 'source': 'module'})

            custom_words_text = request.form.getlist('custom_words[]')
            custom_translations_text = request.form.getlist('custom_translations[]')
            for cw_text, ct_text in zip(custom_words_text, custom_translations_text):
                if cw_text and ct_text:
                    words_data_source.append({'word': cw_text, 'perevod': ct_text, 'source': 'custom'})
        
        # Create Test object
        new_test = Test(**new_test_params)
        db.session.add(new_test)
        db.session.commit() # Commit to get new_test.id so TestWord entries can be linked
        
        # АВТОМАТИЧЕСКАЯ ОЧИСТКА РЕЗУЛЬТАТОВ ПРЕДЫДУЩИХ ТЕСТОВ
        try:
            results_cleared_count, tests_affected = auto_clear_previous_test_results(
                teacher_user=user,
                class_number=class_number,
                new_test_id=new_test.id
            )
            
            if results_cleared_count > 0:
                affected_tests_str = ", ".join(tests_affected[:3])  # Показываем первые 3 теста
                if len(tests_affected) > 3:
                    affected_tests_str += f" и еще {len(tests_affected) - 3}"
                
                test_type_str = "активных тестов" if CLEAR_ONLY_ACTIVE_TESTS else "тестов"
                flash(f"Автоматически очищено {results_cleared_count} результатов из {test_type_str} для класса {class_number} ({affected_tests_str}).", "info")
            
        except Exception as e:
            # Если произошла ошибка при очистке, не прерываем создание теста
            # Восстанавливаем состояние для нового теста
            try:
                db.session.rollback()
                db.session.add(new_test)
                db.session.commit()
            except:
                pass  # Если и это не удалось, продолжаем
            
            print(f"Ошибка при автоматической очистке результатов: {e}")
            flash("Тест создан, но не удалось очистить результаты предыдущих тестов.", "warning")

        # Final processing of words_data_source based on general word_order and word_count
        # (This was previously somewhat mixed with initial fetching)

        # 1. Shuffle if overall word_order is 'random'
        if new_test.word_order == 'random':
            random.shuffle(words_data_source)
        
        # 2. Apply general word_count as a final limiter, 
        #    but only if it hasn't been specifically set by 'random_from_module' dictation.
        #    For 'all_module' and 'selected_specific' dictation, word_count_form acts as the limiter.
        #    For non-dictation tests, word_count_form acts as the limiter.
        
        final_word_count_to_use = new_test.word_count # This comes from new_test_params

        if final_word_count_to_use is not None and final_word_count_to_use > 0:
            if len(words_data_source) > final_word_count_to_use:
                words_data_source = words_data_source[:final_word_count_to_use]
        elif final_word_count_to_use == 0: # Explicitly 0 means no words (edge case, but good to define)
             words_data_source = []


        # Create test words (The rest of the logic for populating TestWord based on test_type)
        for idx, word_entry in enumerate(words_data_source):
            original_word_text = word_entry['word']
            original_translation = word_entry['perevod']
            
            current_word_for_test_word_model = original_word_text 
            prompt_for_test_word_model = original_translation   
            options_db = None
            missing_letters_positions_db = None
            correct_answer_for_db = original_word_text 

            if test_type == 'add_letter':
                prompt_for_test_word_model = original_translation
                if test_mode == 'random_letters':
                    letter_indices = [i for i, char in enumerate(original_word_text) if char != ' ']
                    num_actual_letters = len(letter_indices)

                    if num_actual_letters > 0:
                        # Determine base number of letters to remove based on actual letter count
                        if num_actual_letters <= 3:
                            val = 1
                        elif num_actual_letters <= 6:
                            val = random.randint(1, 2)
                        elif num_actual_letters <= 9:
                            val = random.randint(2, 3)
                        else: # 10+ actual letters
                            val = random.randint(3, 4)

                        # Adjust num_letters_to_remove
                        if num_actual_letters == 1: # For a single letter word, always remove that one letter
                            num_letters_to_remove = 1
                        else:
                            # For words with more than one letter, remove at most half, but at least 1
                            num_letters_to_remove = min(val, num_actual_letters // 2)
                            num_letters_to_remove = max(1, num_letters_to_remove)

                        positions_zero_indexed = sorted(random.sample(letter_indices, num_letters_to_remove))
                        
                        actual_missing_letters_list = [original_word_text[pos] for pos in positions_zero_indexed]
                        correct_answer_for_db = "".join(actual_missing_letters_list)
                        
                        word_with_gaps_list = list(original_word_text)
                        for pos in positions_zero_indexed:
                            word_with_gaps_list[pos] = '_'
                        current_word_for_test_word_model = "".join(word_with_gaps_list)
                        missing_letters_positions_db = ','.join(str(pos + 1) for pos in positions_zero_indexed) # Store 1-indexed

                    else: # No actual letters in original_word_text (it's empty or all spaces)
                        current_word_for_test_word_model = original_word_text
                        correct_answer_for_db = ""
                        missing_letters_positions_db = ""
                elif test_mode == 'manual_letters':
                    # For manual mode, initially save the original word.
                    # Configuration will happen in a separate step via configure_test_words.
                    current_word_for_test_word_model = original_word_text
                    # prompt_for_test_word_model is already set
                    correct_answer_for_db = ""  # Intentionally blank, to be filled in config step
                    missing_letters_positions_db = None  # To be filled in config step
                    # Removed logic that tried to get 'manual_missing_indices_for_words' here.
                    # Removed flash messages regarding missing manual indices here.
                        
            elif test_type == 'multiple_choice_single':
                test_direction = new_test.test_direction or 'word_to_translation'
                
                if test_direction == 'word_to_translation':
                    current_word_for_test_word_model = original_word_text
                    prompt_for_test_word_model = "Выберите правильный перевод:"
                    correct_answer_for_db = original_translation
                else:  # translation_to_word
                    current_word_for_test_word_model = original_translation
                    prompt_for_test_word_model = "Выберите правильное слово:"
                    correct_answer_for_db = original_word_text
                
                # Используем новую функцию для генерации вариантов
                options_list = generate_options_with_fallback(
                    word_entry, selected_modules, class_number, test_direction
                )
                options_db = '|'.join(options_list)

            elif test_type == 'dictation':
                # Student hears/sees translation (prompt) and types the word (correct_answer).
                # `word` field can be empty or show underscores matching word length as a visual cue.
                current_word_for_test_word_model = ''.join(['_'] * len(original_word_text)) # Visual cue for length
                prompt_for_test_word_model = original_translation 
                correct_answer_for_db = original_word_text

            elif test_type == 'true_false':
                # The 'word' field will store the statement. Teacher needs UI to define statement & if T/F.
                # Placeholder: Assume statement is "Word - Translation" and it's True.
                # For custom words, teacher would input the statement and T/F.
                # This part requires significant teacher input for meaningful questions.
                if word_entry['source'] == 'custom': # Assume custom word text *is* the statement
                    current_word_for_test_word_model = original_word_text
                    # And custom translation *is* the True/False value
                    correct_answer_for_db = original_translation if original_translation.lower() in ['true', 'false'] else "True"
                else: # From module
                    # Determine if the statement should be true or false
                    if random.choice([True, False]):
                        # Make a true statement
                        current_word_for_test_word_model = f"{original_word_text} - {original_translation}"
                        correct_answer_for_db = "True"
                    else:
                        # Try to make a false statement
                        # Need to get current class and unit for the original_word_text to find distractors
                        # This assumes word_entry might have class/unit/module if it's from a module.
                        # If not, this part needs refinement on how to get context for distractors.
                        # For now, using the overall test's class_number.
                        # And assuming unit/module context might be in new_test_params if available,
                        # otherwise, this might be too broad or too narrow.

                        # Attempt to find a distractor translation from the same class.
                        # More specific (unit/module) would be better if that context is reliably available here.
                        distractor_words = Word.query.filter(
                            Word.classs == new_test_params.get('classs'),
                            Word.word != original_word_text # Exclude the original word itself
                        ).all()

                        if distractor_words:
                            distractor_word_obj = random.choice(distractor_words)
                            distractor_translation = distractor_word_obj.perevod

                            # Ensure the distractor translation isn't the same as the original,
                            # which could happen if different words have the same translation.
                            if distractor_translation != original_translation:
                                current_word_for_test_word_model = f"{original_word_text} - {distractor_translation}"
                                correct_answer_for_db = "False"
                            else:
                                # Fallback: if distractor is same as original, make it a true statement
                                current_word_for_test_word_model = f"{original_word_text} - {original_translation}"
                                correct_answer_for_db = "True"
                        else:
                            # Fallback: if no distractors found, make it a true statement
                            current_word_for_test_word_model = f"{original_word_text} - {original_translation}"
                            correct_answer_for_db = "True"
                
                prompt_for_test_word_model = "Верно или неверно?" 
                options_db = "True|False"
                
            elif test_type == 'fill_word':
                # Student sees translation (word field) and needs to write the original word (correct_answer).
                current_word_for_test_word_model = original_translation # This is shown to the student as the question/prompt
                prompt_for_test_word_model = "Впишите соответствующее слово (оригинал):"
                correct_answer_for_db = original_word_text

            elif test_type == 'multiple_choice_multiple':
                # Question is the translation/prompt. Options are words. Multiple can be correct.
                # Teacher needs UI to select multiple correct answers. This is a complex setup.
                # Placeholder: Treat like single choice for now, teacher defines one correct answer.
                current_word_for_test_word_model = original_translation # Question: "Select all words that mean X"
                prompt_for_test_word_model = "Выберите все подходящие варианты:"
                correct_answer_for_db = original_word_text # Placeholder: single correct answer.
                                                    # Real implementation: "ans1|ans2"
                
                all_other_words_in_class = [w.word for w in Word.query.filter(Word.classs == class_number, Word.word != original_word_text).all()]
                num_options_total = 4 
                
                # This logic is simplified; creating diverse and multiple correct options needs more.
                # For now, generate options similar to single choice.
                num_wrong_options_needed = num_options_total - 1 # Assuming 1 correct for now
                
                wrong_options_list = []
                if len(all_other_words_in_class) >= num_wrong_options_needed:
                    wrong_options_list = random.sample(all_other_words_in_class, num_wrong_options_needed)
                else:
                    wrong_options_list = all_other_words_in_class
                
                current_options_list_for_db = wrong_options_list + [original_word_text]
                # Fill with placeholders if not enough unique words
                while len(current_options_list_for_db) < num_options_total:
                    current_options_list_for_db.append(f"Вариант {len(current_options_list_for_db)+1}")

                random.shuffle(current_options_list_for_db)
                options_db = '|'.join(current_options_list_for_db[:num_options_total])


            test_word_entry = TestWord(
                test_id=new_test.id,
                word=current_word_for_test_word_model,    # What the student sees as the question/task item
                perevod=prompt_for_test_word_model,       # Supporting info, like translation or detailed prompt
                correct_answer=correct_answer_for_db,
                options=options_db,
                missing_letters=missing_letters_positions_db,
                word_order=idx
            )
            db.session.add(test_word_entry)

        db.session.commit() # Commit TestWord entries. Test object (new_test) was committed earlier.

        # Use new_test.type and new_test.test_mode for the redirect condition
        if new_test.type == 'add_letter' and new_test.test_mode == 'manual_letters':
            flash("Тест создан. Теперь укажите, какие буквы пропустить в словах.", "info")
            return redirect(url_for('configure_test_words', test_id=new_test.id))
        else:
            flash("Тест успешно создан!", "success")
            return redirect(url_for('test_details', test_id=new_test.id))

    # GET request:
    user = db.session.get(User, session['user_id']) # Ensure user is fetched for GET request as well
    # Fetch available modules to populate the form (example, adjust as per actual logic)
    available_modules = {} # Replace with actual module fetching logic if needed for the GET request
    classes_get = [str(i) for i in range(1, 12)]
    
    # Pass any other necessary context for the template
    return render_template("create_test.html", user=user, classes=classes_get, available_modules=available_modules)

@app.route('/configure_test_words/<int:test_id>', methods=['GET', 'POST'])
def configure_test_words(test_id):
    if 'user_id' not in session:
        flash("Доступ запрещен. Пожалуйста, войдите.", "warning")
        return redirect(url_for('auth.login'))
    
    user = db.session.get(User, session['user_id'])
    if not user or user.teacher != 'yes':
        flash("Доступ запрещен. Только учителя могут настраивать тесты.", "warning")
        return redirect(url_for('tests'))

    test = Test.query.get_or_404(test_id)
    
    if test.created_by != user.id:
        flash("Вы не можете редактировать этот тест, так как не являетесь его создателем.", "danger")
        return redirect(url_for('tests'))

    if not (test.type == 'add_letter' and test.test_mode == 'manual_letters'):
        flash("Этот тест не требует ручной настройки пропущенных букв.", "info")
        return redirect(url_for('test_details', test_id=test.id))

    test_words_for_config = TestWord.query.filter_by(test_id=test.id).order_by(TestWord.word_order).all()

    if request.method == 'POST':
        try:
            for word_obj in test_words_for_config:
                # In the create_test step, word_obj.word stored the original_word_text
                original_word_text = word_obj.word 
                submitted_indices_str = request.form.get(f'word_{word_obj.id}_indices')

                if submitted_indices_str:
                    positions_zero_indexed = sorted(list(set(
                        [int(p.strip()) for p in submitted_indices_str.split(',') if p.strip().isdigit()]
                    )))
                    
                    valid_positions = [p for p in positions_zero_indexed if 0 <= p < len(original_word_text)]

                    if valid_positions:
                        actual_missing_letters_list = [original_word_text[pos] for pos in valid_positions]
                        word_obj.correct_answer = "".join(actual_missing_letters_list)
                        
                        word_with_gaps_list = list(original_word_text)
                        for pos in valid_positions:
                            word_with_gaps_list[pos] = '_'
                        # Update word_obj.word to store the word with gaps for student view
                        word_obj.word = "".join(word_with_gaps_list) 
                        word_obj.missing_letters = ','.join(str(pos + 1) for pos in valid_positions) # Store 1-indexed
                    else:
                        # No valid indices submitted (e.g., empty string or out-of-bound numbers)
                        word_obj.word = original_word_text # Keep original word (no gaps)
                        word_obj.correct_answer = ""       # No letters are missing
                        word_obj.missing_letters = None
                        if submitted_indices_str: # If teacher submitted something but it was invalid/empty after parsing
                             flash(f"Для слова '{original_word_text}' не были указаны корректные позиции букв или они были вне диапазона. Пропуски не созданы.", "warning")
                else:
                    # No indices submitted for this word at all, treat as "no letters hidden"
                    word_obj.word = original_word_text
                    word_obj.correct_answer = ""
                    word_obj.missing_letters = None
                    # Optional: flash message if you want to inform that a word was skipped
                    # flash(f"Для слова '{original_word_text}' не указаны буквы для пропуска. Слово сохранено без изменений.", "info")
            
            db.session.commit()
            flash("Настройки пропущенных букв успешно сохранены!", "success")
            return redirect(url_for('test_details', test_id=test.id))
        
        except ValueError as ve:
            db.session.rollback()
            flash(f"Ошибка в формате указанных позиций. Пожалуйста, вводите номера букв через запятую (например, 0,2). {str(ve)}", "danger")
        except Exception as e:
            db.session.rollback()
            flash(f"Произошла непредвиденная ошибка при сохранении настроек: {str(e)}", "error")
            
    # GET request: fetch words and render the configuration template
    # Pre-calculate 0-indexed display strings for missing letter indices.
    for word_obj_from_db in test_words_for_config:
        display_indices_value = ""
        if word_obj_from_db.missing_letters:
            try:
                # missing_letters is 1-indexed from DB, e.g., "1,3,5"
                one_indexed_indices = [int(x.strip()) for x in word_obj_from_db.missing_letters.split(',') if x.strip().isdigit()]
                # Convert to 0-indexed for form display, e.g., "0,2,4"
                zero_indexed_indices = [str(idx - 1) for idx in one_indexed_indices if idx > 0] # ensure idx-1 is non-negative
                display_indices_value = ','.join(zero_indexed_indices)
            except ValueError:
                # If parsing fails (e.g., non-integer data), pass empty string.
                # Consider logging this case.
                display_indices_value = "" 
        
        # Dynamically add the pre-calculated string as an attribute to the object for easy template access
        setattr(word_obj_from_db, 'display_indices_for_form', display_indices_value)

    # Pass the (now modified with .display_indices_for_form) test_words_for_config to the template.
    return render_template('configure_test_words.html', test=test, test_words=test_words_for_config, user=user)

@app.route('/configure_true_false_test/<int:test_id>', methods=['GET', 'POST'])
def configure_true_false_test(test_id):
    if 'user_id' not in session:
        flash("Доступ запрещен. Пожалуйста, войдите.", "warning")
        return redirect(url_for('auth.login'))
    
    user = db.session.get(User, session['user_id'])
    if not user or user.teacher != 'yes':
        flash("Доступ запрещен. Только учителя могут настраивать тесты.", "warning")
        return redirect(url_for('tests'))

    test = Test.query.get_or_404(test_id)
    
    if test.created_by != user.id:
        flash("Вы не можете редактировать этот тест, так как не являетесь его создателем.", "danger")
        return redirect(url_for('tests'))

    if test.type != 'true_false':
        flash("Этот маршрут предназначен только для тестов типа 'true_false'.", "info")
        return redirect(url_for('test_details', test_id=test.id))

    test_words = TestWord.query.filter_by(test_id=test.id).order_by(TestWord.word_order).all()

    if request.method == 'POST':
        try:
            for word in test_words:
                # Получаем данные из формы для каждого слова
                statement = request.form.get(f'statement_{word.id}', '').strip()
                prompt = request.form.get(f'prompt_{word.id}', '').strip()
                correct_answer = request.form.get(f'correct_answer_{word.id}', '').strip()
                
                if statement and correct_answer:
                    word.word = statement
                    word.perevod = prompt if prompt else "Верно или неверно?"
                    word.correct_answer = correct_answer
            
            db.session.commit()
            flash("Настройки теста true/false успешно сохранены!", "success")
            return redirect(url_for('test_details', test_id=test.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Произошла ошибка при сохранении настроек: {str(e)}", "error")
    
    return render_template('configure_true_false_test.html', test=test, test_words=test_words, user=user)

@app.route("/test/<int:test_id>")
def test_details(test_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = db.session.get(User, session['user_id'])
    if not user:
        session.pop('user_id', None)
        flash("Пользователь не найден, пожалуйста, войдите снова.", "error")
        return redirect(url_for('auth.login'))

    test = Test.query.get_or_404(test_id)
    
    if user.teacher == 'yes':
        # Teacher's view: Gather student progress and render details page
        students_in_class = User.query.filter_by(class_number=test.classs, teacher='no').all()
        total_students_in_class = len(students_in_class)
        all_results_for_test = TestResult.query.filter(
            TestResult.test_id == test.id,
            TestResult.started_at >= test.created_at
        ).all()

        completed_students_details = []
        in_progress_students_details = []
        not_started_student_ids = {s.id for s in students_in_class}

        for result in all_results_for_test:
            student_user = db.session.get(User, result.user_id)
            if not student_user or student_user.teacher == 'yes': # Skip non-students or if user somehow deleted
                if student_user and result.user_id in not_started_student_ids:
                    not_started_student_ids.remove(result.user_id)
                continue

            if result.user_id in not_started_student_ids:
                not_started_student_ids.remove(result.user_id)
            
            if result.completed_at:
                completed_students_details.append({'user': student_user, 'result': result})
            else:
                item_data_for_template = {
                    'user': student_user,
                    'result': result,
                    'remaining_time_display': "Без ограничений",
                    'has_time_limit': False,
                    'end_time_utc_iso': None
                }
                if test.time_limit and test.time_limit > 0:
                    end_time_utc = result.started_at + timedelta(minutes=test.time_limit)
                    now_utc = datetime.utcnow()
                    item_data_for_template['has_time_limit'] = True
                    item_data_for_template['end_time_utc_iso'] = end_time_utc.isoformat() + "Z"
                    if now_utc < end_time_utc:
                        remaining_delta = end_time_utc - now_utc
                        hours, remainder = divmod(remaining_delta.total_seconds(), 3600)
                        minutes, seconds_float = divmod(remainder, 60)
                        seconds = int(seconds_float)
                        if hours > 0:
                            item_data_for_template['remaining_time_display'] = f"{int(hours)}h {int(minutes)}m {seconds}s left"
                        else:
                            item_data_for_template['remaining_time_display'] = f"{int(minutes)}m {seconds}s left"
                    else:
                        item_data_for_template['remaining_time_display'] = "Время вышло"
                in_progress_students_details.append(item_data_for_template)

        not_started_students = [db.session.get(User, uid) for uid in not_started_student_ids]
        not_started_students = [s for s in not_started_students if s] 
        
        completed_count = len(completed_students_details)
        progress_percentage = (completed_count / total_students_in_class * 100) if total_students_in_class > 0 else 0

        return render_template('test_details.html',
                             test=test,
                             total_students_in_class=total_students_in_class,
                             completed_students_details=completed_students_details,
                             in_progress_students_details=in_progress_students_details,
                             not_started_students=not_started_students,
                             progress_percentage=progress_percentage,
                             is_teacher=True) # Ensure is_teacher is passed
    
    # --- STUDENT PATH --- (if user.teacher == 'no')
    else:
        student_completed_result = TestResult.query.filter_by(
            test_id=test.id,
            user_id=user.id
        ).filter(TestResult.completed_at.isnot(None)).order_by(TestResult.completed_at.desc()).first()

        if not test.is_active: # Test is ARCHIVED
            if student_completed_result:
                flash("Этот тест находится в архиве. Просмотр ваших результатов.", "info")
                return redirect(url_for('test_results', test_id=test.id, result_id=student_completed_result.id))
            else:
                flash("Этот тест находится в архиве, и вы его не проходили.", "warning")
                return redirect(url_for('tests'))
        else: # Test is ACTIVE
            if student_completed_result:
                flash("Вы уже завершили этот тест. Просмотр ваших результатов.", "info")
                return redirect(url_for('test_results', test_id=test.id, result_id=student_completed_result.id))
            else:
                # If active and not completed (or no result at all), student should be able to take it.
                return redirect(url_for('take_test', test_link=test.link))
    
    # Fallback for any unhandled student cases, though the logic above should cover students.
    # This line should ideally not be reached if student logic is complete.
    flash("Не удалось отобразить детали теста для вашего статуса.", "warning")
    return redirect(url_for('tests'))

@app.route("/test/<int:test_id>/archive", methods=['POST'])
def archive_test(test_id):
    if 'user_id' not in session:
        flash("Доступ запрещен. Пожалуйста, войдите как учитель.", "warning")
        return redirect(url_for('auth.login'))

    user = db.session.get(User, session['user_id'])
    if not user or user.teacher != 'yes':
        flash("Только создатель теста может его архивировать.", "warning")
        if not user: session.pop('user_id', None)
        return redirect(url_for('tests')) # Or back to test_details

    test = Test.query.get_or_404(test_id)
    if test.created_by != user.id:
        return redirect('/tests', 302)

    test.is_active = False
    db.session.commit()
    return redirect(url_for('test_details', test_id=test_id))

@app.route("/test/<int:test_id>/unarchive", methods=['POST'])
def unarchive_test(test_id):
    if 'user_id' not in session:
        flash("Доступ запрещен. Пожалуйста, войдите как учитель.", "warning")
        return redirect(url_for('auth.login'))

    user = db.session.get(User, session['user_id'])
    if not user or user.teacher != 'yes':
        flash("Только создатель теста может его восстановить из архива.", "warning")
        if not user: session.pop('user_id', None)
        return redirect(url_for('tests'))

    test = Test.query.get_or_404(test_id)
    if test.created_by != user.id:
        flash("Только создатель теста может его восстановить.", "warning")
        return redirect(url_for('test_details', test_id=test_id))

    test.is_active = True
    db.session.commit()
    flash(f"Тест '{test.title}' успешно восстановлен из архива.", "success")
    return redirect(url_for('test_details', test_id=test_id))

@app.route("/test/<int:test_id>/clear_results", methods=['POST'])
def clear_test_results(test_id):
    if 'user_id' not in session:
        flash("Доступ запрещен. Пожалуйста, войдите как учитель.", "warning")
        return redirect(url_for('auth.login'))

    user = db.session.get(User, session['user_id'])
    if not user or user.teacher != 'yes':
        flash("Только создатель теста может очистить его результаты.", "warning")
        if not user: session.pop('user_id', None)
        return redirect(url_for('tests')) # Or back to test_details

    test = Test.query.get_or_404(test_id)
    if test.created_by != user.id:
        flash("Только создатель теста может очистить его результаты.", "warning")
        return redirect(url_for('test_details', test_id=test_id))

    results_to_delete = TestResult.query.filter_by(test_id=test.id).all()
    
    if not results_to_delete:
        flash(f"Нет результатов для очистки для теста '{test.title}'.", "info")
        return redirect(url_for('test_details', test_id=test_id))

    try:
        for result in results_to_delete:
            # Explicitly delete TestAnswer objects associated with this result
            TestAnswer.query.filter_by(test_result_id=result.id).delete(synchronize_session=False)
            # Also delete TextTestAnswer objects for text-based tests
            TextTestAnswer.query.filter_by(test_result_id=result.id).delete(synchronize_session=False)
            # Now delete the TestResult object
            db.session.delete(result)
        
        db.session.commit()
        flash(f"Все результаты для теста '{test.title}' были успешно удалены.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при удалении результатов теста: {str(e)}", "error")
        # app.logger.error(f"Error clearing test results for test_id {test_id}: {e}") # Requires app.logger to be configured
        print(f"Error clearing test results for test_id {test_id}: {e}") # simple print for now

    return redirect(url_for('test_details', test_id=test_id))

@app.route("/test/<int:test_id>/delete", methods=['POST'])
def delete_test_completely(test_id):
    if 'user_id' not in session:
        flash("Доступ запрещен. Пожалуйста, войдите как учитель.", "warning")
        return redirect(url_for('auth.login'))

    user = db.session.get(User, session['user_id'])
    if not user or user.teacher != 'yes':
        flash("Только создатель теста может его удалить.", "warning")
        if not user: session.pop('user_id', None)
        return redirect(url_for('tests'))

    test_to_delete = Test.query.get_or_404(test_id)
    if test_to_delete.created_by != user.id:
        flash("Только создатель теста может его удалить.", "warning")
        return redirect(url_for('test_details', test_id=test_id))

    try:
        # Delete associated TestAnswer entries
        TestAnswer.query.filter(TestAnswer.test_result_id.in_(db.session.query(TestResult.id).filter_by(test_id=test_id))).delete(synchronize_session=False)
        # Delete associated TestResult entries
        TestResult.query.filter_by(test_id=test_id).delete(synchronize_session=False)
        # Delete associated TestWord entries
        TestWord.query.filter_by(test_id=test_id).delete(synchronize_session=False)
        
        db.session.delete(test_to_delete)
        db.session.commit()
        flash(f"Тест '{test_to_delete.title}' и все связанные с ним данные были успешно удалены.", "success")
        return redirect(url_for('tests'))
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при удалении теста: {str(e)}", "error")
        return redirect(url_for('test_details', test_id=test_id))

@app.route('/take_test/<test_link>', methods=['GET', 'POST'])
def take_test(test_link):
    if 'user_id' not in session:
        flash("Пожалуйста, войдите в систему, чтобы пройти тест.", "error")
        return redirect(url_for('auth.login'))

    current_user = db.session.get(User, session['user_id'])
    if not current_user:
        session.pop('user_id', None)
        flash("Пользователь не найден, пожалуйста, войдите снова.", "error")
        return redirect(url_for('auth.login'))
    
    test = Test.query.filter_by(link=test_link).first_or_404()

    # Отладочная информация о сессии
    print(f"DEBUG: Session data at take_test start: {dict(session)}")
    print(f"DEBUG: Current user: {current_user.nick}, ID: {current_user.id}")
    print(f"DEBUG: Test ID: {test.id}, Test Link: {test.link}")

    # Check if student belongs to the correct class for the test
    if current_user.teacher == 'no' and test.classs != current_user.class_number:
        flash("Вы не можете пройти этот тест, так как он предназначен для другого класса.", "error")
        return redirect(url_for('tests'))

    # Check if the test is active (students cannot take archived tests)
    # Teachers can preview archived tests they created (handled in test_id route)
    if current_user.teacher == 'no' and not test.is_active:
        flash("Этот тест больше не активен и не может быть пройден.", "error")
        return redirect(url_for('tests'))

    # POST request: Starting the test
    if request.method == 'POST':
        if current_user.teacher == 'yes':
            # Teachers starting a test go directly to preview mode via test_id route
            # No TestResult is created for them.
            flash("Начат предпросмотр теста.", "info")
            # Явно сохраняем сессию для учителя
            session['is_teacher_preview'] = True
            session['test_link'] = test.link
            session.modified = True
            print(f"DEBUG: Teacher preview mode activated, session: {dict(session)}")
            return jsonify({'success': True, 'redirect_url': '/test/' + test.link})

        # --- STUDENT LOGIC FOR POST (starting a test) ---
        if test.classs != current_user.class_number:
            flash("Вы не можете начать этот тест, так как он предназначен для другого класса.", "error")
            return jsonify({'success': False, 'error': 'Класс не совпадает', 'redirect_url': url_for('tests')}), 403
        if not test.is_active:
            flash("Этот тест больше не активен и не может быть начат.", "error")
            return jsonify({'success': False, 'error': 'Тест не активен', 'redirect_url': url_for('tests')}), 403

        # Check for existing incomplete result for student
        existing_incomplete_result = TestResult.query.filter_by(
            test_id=test.id,
            user_id=current_user.id,
            completed_at=None
        ).first()

        if existing_incomplete_result:
            # If student already has an incomplete test, use that one
            session['active_test_result_id'] = existing_incomplete_result.id
            session['test_link'] = test.link
            # Явно помечаем сессию как измененную
            session.modified = True
            print(f"DEBUG: Using existing test result, ID: {existing_incomplete_result.id}, session: {dict(session)}")
            
            # Вместо JSON-ответа делаем прямой редирект
            resp = make_response(redirect('/test/' + test.link))
            resp.set_cookie('active_test_result_id', str(existing_incomplete_result.id))
            resp.set_cookie('test_link', test.link)
            return resp
        else:
            # If no incomplete test, check if they completed it before.
            # Depending on policy, you might prevent retakes or allow new attempts.
            # For now, let's allow a new attempt if previous was completed or none exists.
            
            # Create a new TestResult for the student
            new_test_result = TestResult(
                test_id=test.id,
                user_id=current_user.id,
                total_questions=len(test.test_words) if test.test_words else 0,
                started_at=datetime.utcnow()
            )
            db.session.add(new_test_result)
            db.session.commit()
            
            session['active_test_result_id'] = new_test_result.id
            session['test_link'] = test.link
            # Явно помечаем сессию как измененную
            session.modified = True
            print(f"DEBUG: Created new test result, ID: {new_test_result.id}, session: {dict(session)}")
            
            # Вместо JSON-ответа делаем прямой редирект
            resp = make_response(redirect('/test/' + test.link))
            resp.set_cookie('active_test_result_id', str(new_test_result.id))
            resp.set_cookie('test_link', test.link)
            return resp

    # GET request logic:
    if current_user.teacher == 'yes':
        # Teachers see the start page, clicking "Start" will POST and then redirect to preview
        return render_template('test_start.html', test=test, user=current_user)
        
    # --- STUDENT LOGIC FOR GET ---
    # If there's an existing incomplete test result, student should resume it.
    incomplete_result = TestResult.query.filter_by(
        test_id=test.id,
        user_id=current_user.id,
        completed_at=None
    ).first()

    if incomplete_result:
        # If student has an incomplete test, take them directly to it to resume
        session['active_test_result_id'] = incomplete_result.id
        session['test_link'] = test.link
        # Явно помечаем сессию как измененную
        session.modified = True
        print(f"DEBUG: Resuming incomplete test, ID: {incomplete_result.id}, session: {dict(session)}")
        # Redirect to the test interface itself (test_id handles rendering based on type)
        resp = make_response(redirect('/test/' + test.link))
        resp.set_cookie('active_test_result_id', str(incomplete_result.id))
        resp.set_cookie('test_link', test.link)
        return resp

    # If test is completed, show link to results or message
    completed_result = TestResult.query.filter(
        TestResult.test_id == test.id,
        TestResult.user_id == current_user.id,
        TestResult.completed_at.isnot(None)
    ).order_by(TestResult.completed_at.desc()).first()

    if completed_result:
        flash("Вы уже завершили этот тест. Посмотрите свои результаты.", "info")
        if test.type == 'text_based':
            return redirect(url_for('view_text_test_result', test_result_id=completed_result.id))
        else:
            return redirect(url_for('test_results', test_id=test.id, result_id=completed_result.id))

    # Otherwise, show the test start page (if it's a GET request and no active/completed test for this user)
    return render_template('test_start.html', test=test, user=current_user)

@app.route('/submit_test/<int:test_id>', methods=['POST'])
def submit_test(test_id):
    if 'user_id' not in session:
        # For form submissions, redirect is more appropriate than JSON error
        flash("Аутентификация не пройдена. Пожалуйста, войдите снова.", "error")
        return redirect(url_for('auth.login'))

    user = db.session.get(User, session['user_id'])
    if not user:
        flash("Пользователь не найден. Пожалуйста, войдите снова.", "error")
        return redirect(url_for('auth.login'))

    test = Test.query.get_or_404(test_id)
    active_test_result = TestResult.query.filter_by(
        test_id=test.id,
        user_id=user.id,
        completed_at=None
    ).first()

    if not active_test_result:
        # This might happen if user tries to submit to a test they haven't started
        # or if they refresh the submit page after already submitting.
        # Check if a completed result exists to redirect to results page.
        completed_result = TestResult.query.filter_by(
            test_id=test.id,
            user_id=user.id
        ).filter(TestResult.completed_at.isnot(None)).order_by(TestResult.completed_at.desc()).first()
        if completed_result:
            flash("Вы уже завершили этот тест.", "info")
            if test.type == 'text_based':
                return redirect(url_for('view_text_test_result', test_result_id=completed_result.id))
            else:
                return redirect(url_for('test_results', test_id=test.id, result_id=completed_result.id))
        else:
            flash("Не найдено активного прохождения теста для отправки. Пожалуйста, начните тест.", "warning")
            return redirect(url_for('take_test', test_link=test.link)) # Or to tests list

    # Server-side time limit check before processing answers
    if test.time_limit and test.time_limit > 0 and active_test_result.started_at:
        allowed_duration = timedelta(minutes=test.time_limit)
        # Add a small grace period (e.g., 5-10 seconds) to account for submission latency
        grace_period = timedelta(seconds=10)
        actual_time_limit_on_server = active_test_result.started_at + allowed_duration + grace_period
        
        if datetime.utcnow() > actual_time_limit_on_server:
            # Time is definitively up on the server
            flash("Время на выполнение теста истекло. Ответы, отправленные после истечения времени, не засчитаны.", "error")
            
            if not active_test_result.completed_at: # Ensure we only complete it once
                active_test_result.completed_at = active_test_result.started_at + allowed_duration # Mark completion at the exact intended end time
                # Calculate time taken for timeout case (should be exactly the time limit)
                if active_test_result.started_at:
                    active_test_result.time_taken = test.time_limit  # Time limit in minutes
                else:
                    active_test_result.time_taken = 0
                # Optionally, set score to 0 if no answers are accepted post-deadline
                # This depends on whether partial/in-time answers were already saved progressively.
                # For the current setup, it implies answers submitted with this request are too late.
                # If you want to be very strict and not rely on progressively saved state (which isn't fully there for add_letter):
                # active_test_result.score = 0
                # active_test_result.correct_answers = 0
                # active_test_result.answers = json.dumps({}) # Clear any answers if submission is void
                # However, if the client *did* submit something just before this server check, 
                # but the check still determines it's too late, those answers won't be processed by the code below.
                # The most straightforward for now is to ensure it's marked completed and then redirect.
                # The scoring logic below will not run if we redirect here.
                
            db.session.commit()
            return redirect(url_for('test_results', test_id=test.id, result_id=active_test_result.id))

    # data = request.get_json() # Changed to use request.form for standard HTML form submission
    submitted_answers_map = {}
    if test.type == 'add_letter':
        # For add_letter, reconstruct answers from individual input boxes
        # Inputs are named like: answer_{test_word.id}_{input_index_in_word}
        for key, value in request.form.items():
            if key.startswith('answer_'):
                parts = key.split('_')
                if len(parts) == 3:
                    try:
                        word_id = int(parts[1])
                        input_idx = int(parts[2])
                        if word_id not in submitted_answers_map:
                            submitted_answers_map[word_id] = {}
                        submitted_answers_map[word_id][input_idx] = value.strip()
                    except ValueError:
                        # Handle cases where parsing fails, though names should be controlled
                        print(f"Warning: Could not parse form key {key}")
                        pass # Or log an error
    # else: # For other test types, if they were using AJAX and data.get('answers', [])
        # This part would need to be adapted if other test types also switch to form submission
        # For now, let's assume other test types might still send answers differently or need updates
        # If they also submit via form with a simple list-like structure for answers (e.g. answer_0, answer_1):
        # pass # Or retrieve their answers based on their specific form field naming
        # If other tests also submit via form, they might name fields like `answer_{test_word.id}` directly.
        # For now, this path is not fully handled for non-add_letter types if they stop using JSON.
        pass

    # Calculate score based on test type
    current_score_count = 0
    detailed_results_for_db = [] # To store TestAnswer objects
    total_questions = len(test.test_words)
    answers_json_for_db = {} # To store in TestResult.answers (JSON)

    # Ensure test words are ordered by their defined word_order for consistent processing
    ordered_test_words = sorted(test.test_words, key=lambda tw: tw.word_order)

    for test_word in ordered_test_words:
        user_submitted_answer_string = ""
        is_correct = False

        if test.type == 'add_letter':
            if test_word.id in submitted_answers_map:
                # Reconstruct the answer from sorted input characters
                answer_chars = []
                sorted_inputs = sorted(submitted_answers_map[test_word.id].items())
                for _, char_val in sorted_inputs:
                    answer_chars.append(char_val)
                user_submitted_answer_string = "".join(answer_chars)
            # For add_letter, TestWord.correct_answer stores the combined missing letters
            is_correct = user_submitted_answer_string.lower() == test_word.correct_answer.lower()
        
        elif test.type == 'multiple_choice_multiple':
            user_selected_options = sorted(request.form.getlist(f'answer_{test_word.id}'))
            user_submitted_answer_string = "|".join(user_selected_options)

            correct_options_list = sorted(test_word.correct_answer.split('|'))
            actual_correct_string_for_comparison = "|".join(correct_options_list)

            is_correct = user_submitted_answer_string.lower() == actual_correct_string_for_comparison.lower()

        elif test.type == 'multiple_choice_single':
            user_submitted_answer_string = request.form.get(f'answer_{test_word.id}', '').strip()
            is_correct = user_submitted_answer_string.lower() == test_word.correct_answer.lower()
        elif test.type == 'dictation':
            current_word_chars_map = {}
            # Collect all characters for this specific test_word.id
            # Key format: dictation_answer_{test_word.id}_{char_index}
            prefix = f'dictation_answer_{test_word.id}_'
            for key, value in request.form.items():
                if key.startswith(prefix):
                    try:
                        char_idx_str = key[len(prefix):] # Get the part after the prefix
                        char_idx = int(char_idx_str)
                        
                        # Ensure value is a single character, take the first if multiple submitted
                        # maxlength=1 on client side should prevent multiple.
                        char_value = value.strip()
                        if len(char_value) > 1:
                            char_value = char_value[0]
                        # If char_value is empty, it represents an empty box for that position.
                        
                        current_word_chars_map[char_idx] = char_value
                    except ValueError:
                        # Log or handle malformed key if char_idx_str is not an int
                        print(f"Warning: Could not parse char index from key {key} for dictation word {test_word.id}")
                        pass # Ignore malformed keys
            
            answer_chars = []
            if current_word_chars_map:
                # Reconstruct the word by sorting characters by their index.
                # Iterate from 0 up to the maximum index found for this word.
                max_idx_found = -1
                if current_word_chars_map: # Ensure not empty before calling max
                    max_idx_found = max(current_word_chars_map.keys())
                
                for i in range(max_idx_found + 1):
                    answer_chars.append(current_word_chars_map.get(i, "")) # Append char or empty string if index is missing
            
            user_submitted_answer_string = "".join(answer_chars)
            
            # Normalize answers for comparison in dictation
            normalized_user_answer = re.sub(r'[\s\.,!?-]', '', user_submitted_answer_string).lower()
            normalized_correct_answer = re.sub(r'[\s\.,!?-]', '', test_word.correct_answer).lower()
            is_correct = normalized_user_answer == normalized_correct_answer
        elif test.type == 'true_false': # Example
            user_submitted_answer_string = request.form.get(f'answer_{test_word.id}', '').strip()
            is_correct = user_submitted_answer_string.capitalize() == test_word.correct_answer # True/False comparison
        else: # Fallback for other types or if logic is missing
            user_submitted_answer_string = request.form.get(f'answer_{test_word.id}', '').strip()
            is_correct = user_submitted_answer_string.lower() == test_word.correct_answer.lower()
        
        if is_correct:
            current_score_count += 1
        
        answers_json_for_db[str(test_word.id)] = user_submitted_answer_string
        detailed_results_for_db.append({
            'test_word_id': test_word.id,
            'user_answer': user_submitted_answer_string,
            'is_correct': is_correct
        })

    # Update active_test_result
    active_test_result.score = int((current_score_count / total_questions) * 100) if total_questions > 0 else 0
    active_test_result.correct_answers = current_score_count
    active_test_result.total_questions = total_questions # Should already be set at start, but good to confirm
    completion_time = datetime.utcnow()
    active_test_result.completed_at = completion_time
    
    # Calculate time taken in minutes (safe calculation)
    if active_test_result.started_at:
        time_diff = completion_time - active_test_result.started_at
        active_test_result.time_taken = max(0, int(time_diff.total_seconds() / 60))  # Convert to minutes, ensure non-negative
    else:
        active_test_result.time_taken = 0  # Fallback if started_at is missing
        
    active_test_result.answers = json.dumps(answers_json_for_db)
    
    # Add TestAnswer instances
    for ans_data in detailed_results_for_db:
        test_answer_entry = TestAnswer(
            test_result_id=active_test_result.id,
            test_word_id=ans_data['test_word_id'],
            user_answer=ans_data['user_answer'],
            is_correct=ans_data['is_correct']
        )
        db.session.add(test_answer_entry)
    
    # Использование современного API SQLAlchemy
    test = db.session.get(Test, test_id)
    if not test:
        flash('Тест не найден', 'error')
        return redirect(url_for('tests'))
    
    try:
        db.session.commit()
        flash("Тест успешно завершен!", "success")
        return redirect(url_for('test_results', test_id=test.id, result_id=active_test_result.id))
    except Exception as e:
        db.session.rollback()
        flash(f"Произошла ошибка при сохранении результатов теста: {str(e)}", "error")
        # Redirect back to the test page, or a general error page
        return redirect(url_for('take_test', test_link=test.link))

@app.route('/test_results/<int:test_id>/<int:result_id>')
def test_results(test_id, result_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = db.session.get(User, session['user_id'])
    # Использование современного API SQLAlchemy
    test = db.session.get(Test, test_id)
    if not test:
        flash('Тест не найден', 'error')
        return redirect(url_for('tests'))
    
    result = db.session.get(TestResult, result_id)
    if not result:
        flash('Результат теста не найден', 'error')
        return redirect(url_for('tests'))
    
    if not user:
        session.pop('user_id', None)
        flash("Пользователь не найден, пожалуйста, войдите снова.", "error")
        return redirect(url_for('auth.login'))

    # Использование современного API SQLAlchemy
    test = db.session.get(Test, test_id)
    if not test:
        flash('Тест не найден', 'error')
        return redirect(url_for('tests'))
    
    result = db.session.get(TestResult, result_id)
    if not result:
        flash('Результат теста не найден', 'error')
        return redirect(url_for('tests'))

    # Verify access to results
    can_view_results = False
    if result.user_id == user.id: # Student viewing their own results
        can_view_results = True
    elif user.teacher == 'yes' and test.created_by == user.id: # Teacher viewing results of a test they created
        can_view_results = True

    if not can_view_results:
        flash("У вас нет доступа для просмотра этих результатов.", "warning")
        return redirect(url_for('tests'))

    # Determine if detailed results should be shown
    show_detailed_results = False  # Default to False
    if user.teacher == 'yes' and test.created_by == user.id:
        # Teacher can always see detailed results for tests they created
        show_detailed_results = True
    elif result.user_id == user.id:  # It's a student viewing their own results
        if not test.is_active:  # Student can see details ONLY if the test is archived
            show_detailed_results = True
        # If the test is active, show_detailed_results remains False for the student

    # Get detailed results if allowed
    detailed_answers = [] 
    if show_detailed_results: # Only fetch if we are going to show them
        for answer_obj in result.test_answers: # answer_obj is a TestAnswer instance
            test_word_instance = answer_obj.test_word # This is the TestWord instance
            
            detailed_answers_item = {
                'user_answer': answer_obj.user_answer,
                'actual_correct_answer': test_word_instance.correct_answer,
                'is_correct': answer_obj.is_correct,
                'options': test_word_instance.options,
                # Initialize parts for add_letter, will be populated below
                'student_reconstructed_parts': None,
                'correct_reconstructed_parts': None
            }

            if test.type == 'add_letter':
                detailed_answers_item['question_presented'] = test_word_instance.word 
                detailed_answers_item['prompt_or_support'] = test_word_instance.perevod

                # Reconstruct student's attempt
                student_parts = []
                gapped_template = test_word_instance.word
                student_letters = list(answer_obj.user_answer)
                s_idx = 0
                correct_letters_iter_for_student = iter(test_word_instance.correct_answer)
                for char_template in gapped_template:
                    part_info = {'char': char_template, 'is_student_input': False, 'is_correct_char': None}
                    if char_template == '_':
                        if s_idx < len(student_letters):
                            part_info['char'] = student_letters[s_idx]
                            part_info['is_student_input'] = True
                            try:
                                correct_char_for_gap = next(correct_letters_iter_for_student)
                                if student_letters[s_idx].lower() == correct_char_for_gap.lower():
                                    part_info['is_correct_char'] = True
                                else:
                                    part_info['is_correct_char'] = False
                            except StopIteration: # More student letters than correct gaps implies mismatch
                                part_info['is_correct_char'] = False
                            s_idx += 1
                        else: # Not enough student letters for this gap
                            part_info['char'] = '_' 
                            part_info['is_student_input'] = True # It was a gap student should have filled
                            part_info['is_correct_char'] = False # Mark as incorrect as it's unfilled
                    student_parts.append(part_info)
                detailed_answers_item['student_reconstructed_parts'] = student_parts

                # Reconstruct correct word display
                correct_parts = []
                correct_letters = list(test_word_instance.correct_answer)
                c_idx = 0
                for char_template in gapped_template:
                    part_info = {'char': char_template, 'is_student_input': False}
                    if char_template == '_':
                        if c_idx < len(correct_letters):
                            part_info['char'] = correct_letters[c_idx]
                            part_info['is_student_input'] = True # It's a filled gap
                            c_idx += 1
                        else:
                            part_info['char'] = '_' # Should not happen if data is consistent
                    correct_parts.append(part_info)
                detailed_answers_item['correct_reconstructed_parts'] = correct_parts
            
            elif test.type == 'multiple_choice_single' or test.type == 'multiple_choice_multiple':
                detailed_answers_item['question_presented'] = test_word_instance.perevod
                detailed_answers_item['prompt_or_support'] = test_word_instance.word
            elif test.type == 'fill_word':
                detailed_answers_item['question_presented'] = test_word_instance.word
                detailed_answers_item['prompt_or_support'] = test_word_instance.perevod
            elif test.type == 'true_false':
                detailed_answers_item['question_presented'] = test_word_instance.word
                detailed_answers_item['prompt_or_support'] = test_word_instance.perevod
            else: # Default for dictation etc.
                detailed_answers_item['question_presented'] = test_word_instance.word 
                detailed_answers_item['prompt_or_support'] = test_word_instance.perevod

            detailed_answers.append(detailed_answers_item)

    # Обработка результатов текстовых тестов
    text_test_results = []
    if test.type == 'text_based' and show_detailed_results:
        questions = []
        if test.text_based_questions:
            try:
                questions = json.loads(test.text_based_questions)
            except json.JSONDecodeError:
                questions = []
        
        # Получение ответов пользователя
        user_answers = {}
        if result.answers:
            try:
                user_answers = json.loads(result.answers)
            except json.JSONDecodeError:
                user_answers = {}
        
        # Подготовка данных для отображения
        for i, question in enumerate(questions):
            question_key = f'question_{i}'
            user_answer = user_answers.get(question_key, '')
            
            # Определение правильности ответа
            is_correct = False
            if question.get('type') == 'mc_single':
                is_correct = user_answer in question.get('correct', [])
            elif question.get('type') == 'mc_multiple':
                if isinstance(user_answer, list):
                    correct_answers = set(question.get('correct', []))
                    user_answers_set = set(user_answer)
                    is_correct = user_answers_set == correct_answers
            elif question.get('type') == 'short_answer':
                correct_answers = question.get('correct', [])
                is_correct = any(user_answer.lower() == correct.lower() for correct in correct_answers)
            
            text_test_results.append({
                'question': question,
                'user_answer': user_answer,
                'is_correct': is_correct,
                'question_number': i + 1
            })

    # Format time taken for display
    time_taken_display = format_time_taken(result.time_taken)
    
    return render_template('test_results.html',
        test=test,
        score=result.score,
        correct_answers=result.correct_answers,
        total_questions=result.total_questions,
        time_taken=time_taken_display,
        time_taken_raw=result.time_taken,  # Raw minutes for any calculations
        incorrect_answers=result.total_questions - result.correct_answers,
        results_summary=detailed_answers, # Changed variable name passed to template
        show_detailed_results=show_detailed_results,
        text_test_results=text_test_results,  # Добавляем результаты текстовых тестов
        is_teacher=user.teacher == 'yes'  # Добавляем информацию о статусе учителя
    )

@app.route("/games")
def games():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = db.session.get(User, session['user_id'])
    if not user:
        session.pop('user_id', None)
        flash("Пользователь не найден, пожалуйста, войдите снова.", "error")
        return redirect(url_for('auth.login'))
        
    return render_template('games.html', is_teacher=user.teacher == 'yes')

# flashcards_select_module and flashcards_game will be moved to games_bp

@app.route('/games/flashcards/select', methods=['GET'])
def flashcards_select_module():
    if 'user_id' not in session:
        return redirect(url_for('auth.login')) # Corrected url_for
    # Fetch all unique classes for the first dropdown
    classes = db.session.query(Word.classs).distinct().order_by(Word.classs).all()
    classes = [c[0] for c in classes if c[0]] # Ensure not None or empty
    return render_template('game_flashcards_select_improved.html', classes=classes)

@app.route('/games/flashcards/<class_name>/<unit_name>/<module_name>')
@app.route('/games/flashcards/<class_name>/<unit_name>')
@app.route('/games/flashcards/<class_name>')
def flashcards_game(class_name, unit_name=None, module_name=None):
    if 'user_id' not in session:
        flash("Пожалуйста, войдите в систему для доступа к флэш-карточкам.", "warning")
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    
    # Получаем параметры игры из URL
    mode = request.args.get('mode', 'specific')
    cards_count = int(request.args.get('cards', 0))  # 0 означает все карточки
    selected_modules = request.args.get('modules', '').split(',') if request.args.get('modules') else []
    selected_units = request.args.get('units', '').split(',') if request.args.get('units') else []
    
    # Определяем какие слова загружать в зависимости от режима
    words_in_module = []
    
    if mode == 'specific' and unit_name and module_name:
        # Конкретный модуль
        words_in_module = Word.query.filter_by(classs=class_name, unit=unit_name, module=module_name).all()
        display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модуль: {module_name}"
    elif mode == 'unit' and unit_name:
        # Весь юнит
        words_in_module = Word.query.filter_by(classs=class_name, unit=unit_name).all()
        display_info = f"Класс: {class_name}, Юнит: {unit_name} (все модули)"
    elif mode == 'class':
        # Весь класс
        words_in_module = Word.query.filter_by(classs=class_name).all()
        display_info = f"Класс: {class_name} (все юниты и модули)"
    elif mode == 'multiple-modules' and unit_name and selected_modules:
        # Несколько выбранных модулей
        words_in_module = Word.query.filter(
            Word.classs == class_name,
            Word.unit == unit_name,
            Word.module.in_(selected_modules)
        ).all()
        display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модули: {', '.join(selected_modules)}"
    elif mode == 'multiple-units' and selected_units:
        # Несколько выбранных юнитов
        words_in_module = Word.query.filter(
            Word.classs == class_name,
            Word.unit.in_(selected_units)
        ).all()
        display_info = f"Класс: {class_name}, Юниты: {', '.join(selected_units)}"
    else:
        # Fallback к конкретному модулю
        if unit_name and module_name:
            words_in_module = Word.query.filter_by(classs=class_name, unit=unit_name, module=module_name).all()
            display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модуль: {module_name}"
        else:
            flash("Неверные параметры игры.", "warning")
            return redirect(url_for('flashcards_select_module'))

    if not words_in_module:
        flash(f"Для выбранных параметров не найдено слов.", "warning")
        return redirect(url_for('flashcards_select_module'))

    augmented_words_list = []
    now = datetime.utcnow()

    for word_obj in words_in_module:
        review_data = UserWordReview.query.filter_by(user_id=user_id, word_id=word_obj.id).first()

        is_new = review_data is None
        next_review_at_iso = None
        interval = None

        if review_data:
            next_review_at_iso = review_data.next_review_at.isoformat()
            interval = review_data.interval_days
            is_due = review_data.next_review_at <= now
        else: # New word, always due
            is_due = True
            # next_review_at_iso remains None for new cards, they will be sorted first.

        augmented_words_list.append({
            'id': word_obj.id,
            'word': word_obj.word,
            'perevod': word_obj.perevod,
            'classs': word_obj.classs,
            'unit': word_obj.unit,
            'module': word_obj.module,
            'next_review_at': next_review_at_iso,
            'interval_days': interval,
            'is_new': is_new,
            'is_due': is_due # Helper for sorting
        })

    # Sort words:
    # 1. Due words (next_review_at <= now or is_new) first.
    # 2. Among due words, sort new ones before reviewed ones.
    # 3. Among reviewed due words, sort by earliest next_review_at.
    # 4. Among not-due words, sort by earliest next_review_at.
    # 5. As a final tie-breaker, shuffle or use word ID. For now, word ID for stability.

    augmented_words_list.sort(key=lambda x: (
        not x['is_due'],  # False (due) comes before True (not due)
        x['next_review_at'] is None, # New words (None) come before reviewed due words
        x['next_review_at'] if x['next_review_at'] else now.isoformat(), # Actual review date, use now for None to group them
        x['id'] # Stable sort by ID as a final tie-breaker
    ))


    # Ограничиваем количество карточек если указано
    if cards_count > 0 and len(augmented_words_list) > cards_count:
        augmented_words_list = augmented_words_list[:cards_count]

    if not augmented_words_list: # Should be caught by words_in_module check, but as a safeguard
        flash(f"Для выбранных параметров не найдено слов.", "warning")
        return redirect(url_for('flashcards_select_module'))

    return render_template('game_flashcards_improved.html',
                           words=augmented_words_list,
                           class_name=class_name,
                           unit_name=unit_name or "Все юниты",
                           module_name=module_name or "Все модули",
                           display_info=display_info,
                           total_cards=len(augmented_words_list),
                           game_mode=mode)

# word_match_select_module and word_match_game will be moved to games_bp

@app.route('/games/word_match/select', methods=['GET'])
def word_match_select_module():
    if 'user_id' not in session:
        return redirect(url_for('auth.login')) # Corrected url_for
    classes = db.session.query(Word.classs).distinct().order_by(Word.classs).all()
    classes = [c[0] for c in classes if c[0]]
    return render_template('game_word_match_select_improved.html', classes=classes)

@app.route('/games/word_match/<class_name>/<unit_name>/<module_name>')
@app.route('/games/word_match/<class_name>/<unit_name>')
@app.route('/games/word_match/<class_name>')
def word_match_game(class_name, unit_name=None, module_name=None):
    if 'user_id' not in session:
        flash("Пожалуйста, войдите в систему.", "warning")
        return redirect(url_for('auth.login'))

    # Получаем параметры игры из URL
    mode = request.args.get('mode', 'specific')
    cards_count = int(request.args.get('cards', 8))  # Количество пар слов
    timer_duration = int(request.args.get('timer', 0))
    enable_stopwatch = request.args.get('stopwatch') == 'true'
    selected_modules = request.args.get('modules', '').split(',') if request.args.get('modules') else []
    selected_units = request.args.get('units', '').split(',') if request.args.get('units') else []

    # Определяем какие слова загружать в зависимости от режима
    all_words = []
    
    if mode == 'specific' and unit_name and module_name:
        # Конкретный модуль
        all_words = Word.query.filter_by(classs=class_name, unit=unit_name, module=module_name).all()
        display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модуль: {module_name}"
    elif mode == 'unit' and unit_name:
        # Весь юнит
        all_words = Word.query.filter_by(classs=class_name, unit=unit_name).all()
        display_info = f"Класс: {class_name}, Юнит: {unit_name} (все модули)"
    elif mode == 'class':
        # Весь класс
        all_words = Word.query.filter_by(classs=class_name).all()
        display_info = f"Класс: {class_name} (все юниты и модули)"
    elif mode == 'multiple-modules' and unit_name and selected_modules:
        # Несколько выбранных модулей
        all_words = Word.query.filter(
            Word.classs == class_name,
            Word.unit == unit_name,
            Word.module.in_(selected_modules)
        ).all()
        display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модули: {', '.join(selected_modules)}"
    elif mode == 'multiple-units' and selected_units:
        # Несколько выбранных юнитов
        all_words = Word.query.filter(
            Word.classs == class_name,
            Word.unit.in_(selected_units)
        ).all()
        display_info = f"Класс: {class_name}, Юниты: {', '.join(selected_units)}"
    else:
        # Fallback к конкретному модулю
        if unit_name and module_name:
            all_words = Word.query.filter_by(classs=class_name, unit=unit_name, module=module_name).all()
            display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модуль: {module_name}"
        else:
            flash("Неверные параметры игры.", "warning")
            return redirect(url_for('word_match_select_module'))

    if not all_words:
        flash(f"Для выбранных параметров не найдено слов.", "warning")
        return redirect(url_for('word_match_select_module'))

    # Ограничиваем количество пар доступным количеством слов
    max_pairs = len(all_words)
    num_pairs = min(cards_count, max_pairs)

    if num_pairs < 2:
        flash(f"Недостаточно слов для игры (нужно хотя бы 2, найдено {max_pairs}).", "warning")
        return redirect(url_for('word_match_select_module'))

    # Выбираем случайные слова
    selected_word_objects = random.sample(all_words, num_pairs)

    original_words_for_js = []
    jumbled_words_list = []
    jumbled_translations_list = []

    for word_obj in selected_word_objects:
        original_words_for_js.append({'id': word_obj.id, 'word': word_obj.word, 'translation': word_obj.perevod})
        jumbled_words_list.append({'id': word_obj.id, 'text': word_obj.word})
        jumbled_translations_list.append({'id': word_obj.id, 'text': word_obj.perevod})

    random.shuffle(jumbled_words_list)
    random.shuffle(jumbled_translations_list)

    return render_template('game_word_match.html',
                           original_words=original_words_for_js,
                           jumbled_words_list=jumbled_words_list,
                           jumbled_translations_list=jumbled_translations_list,
                           class_name=class_name,
                           unit_name=unit_name or "Все юниты",
                           module_name=module_name or "Все модули",
                           display_info=display_info,
                           num_pairs=num_pairs,
                           timer_duration=timer_duration,
                           enable_stopwatch=enable_stopwatch,
                           game_mode=mode)

# sentence_scramble_select_module and sentence_scramble_game will be moved to games_bp

@app.route('/games/sentence_scramble/select', methods=['GET'])
def sentence_scramble_select_module():
    if 'user_id' not in session:
        return redirect(url_for('auth.login')) # Corrected url_for
    # Fetch all unique classes that have sentences
    classes = db.session.query(Sentence.classs).distinct().order_by(Sentence.classs).all()
    classes = [c[0] for c in classes if c[0]]
    return render_template('game_sentence_scramble_select.html', classes=classes)

@app.route('/games/sentence_scramble/<class_name>/<unit_name>/<module_name>')
def sentence_scramble_game(class_name, unit_name, module_name):
    if 'user_id' not in session:
        flash("Пожалуйста, войдите в систему.", "warning")
        return redirect(url_for('auth.login')) # Corrected url_for

    sentences_query = Sentence.query.filter_by(classs=class_name, unit=unit_name, module=module_name).all()

    if not sentences_query:
        flash(f"Для модуля '{module_name}' (юнит '{unit_name}', класс '{class_name}') не найдено предложений.", "warning")
        return redirect(url_for('sentence_scramble_select_module'))

    sentences_for_js = []
    for sentence_obj in sentences_query:
        sentences_for_js.append({
            'id': sentence_obj.id,
            'text': sentence_obj.text,
            'translation': sentence_obj.translation
            # Add other fields like classs, unit, module if needed by JS, but likely not for the game itself
        })

    # Shuffle the list of sentences for the game
    random.shuffle(sentences_for_js)

    return render_template('game_sentence_scramble.html',
                           sentences=sentences_for_js, # Pass the list of sentence dicts
                           class_name=class_name,
                           unit_name=unit_name,
                           module_name=module_name)

# hangman_select_module and hangman_game will be moved to games_bp

@app.route('/games/hangman/select', methods=['GET'])
def hangman_select_module():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    # Fetch all unique classes for the first dropdown
    classes = db.session.query(Word.classs).distinct().order_by(Word.classs).all()
    classes = [c[0] for c in classes if c[0]] # Ensure not None or empty
    return render_template('game_hangman_select_improved.html', classes=classes)

@app.route('/games/hangman/<class_name>/<unit_name>/<module_name>')
def hangman_game(class_name, unit_name, module_name):
    if 'user_id' not in session:
        flash("Пожалуйста, войдите в систему.", "warning")
        return redirect(url_for('auth.login'))

    # Get game settings from URL parameters
    num_words = int(request.args.get('words', 10))  # Default 10 words
    timer_duration = int(request.args.get('timer', 0))  # Default no timer
    enable_stopwatch = request.args.get('stopwatch', 'false').lower() == 'true'
    difficulty = request.args.get('difficulty', 'medium')  # easy, medium, hard
    game_mode = request.args.get('mode', 'specific')  # specific, unit, class, multiple

    # Handle different game modes
    if game_mode == 'unit':
        words_query = Word.query.filter_by(classs=class_name, unit=unit_name).all()
    elif game_mode == 'class':
        words_query = Word.query.filter_by(classs=class_name).all()
    elif game_mode == 'multiple':
        modules = request.args.get('modules', '').split(',')
        if not modules or modules == ['']:
            flash("Не выбраны модули для игры.", "warning")
            return redirect(url_for('hangman_select_module'))
        words_query = Word.query.filter(
            Word.classs == class_name,
            Word.unit == unit_name,
            Word.module.in_(modules)
        ).all()
    else:  # specific module
        words_query = Word.query.filter_by(classs=class_name, unit=unit_name, module=module_name).all()

    if not words_query:
        flash(f"Для выбранного модуля не найдено слов.", "warning")
        return redirect(url_for('hangman_select_module'))

    # Filter words by difficulty if specified
    if difficulty == 'easy':
        # Easy: words 3-5 letters
        words_query = [w for w in words_query if 3 <= len(w.word) <= 5]
    elif difficulty == 'medium':
        # Medium: words 4-8 letters
        words_query = [w for w in words_query if 4 <= len(w.word) <= 8]
    elif difficulty == 'hard':
        # Hard: words 6+ letters
        words_query = [w for w in words_query if len(w.word) >= 6]

    if not words_query:
        flash(f"Для выбранной сложности не найдено подходящих слов.", "warning")
        return redirect(url_for('hangman_select_module'))

    # Limit number of words and shuffle
    if len(words_query) > num_words:
        words_query = random.sample(words_query, num_words)
    else:
        random.shuffle(words_query)

    # Prepare words for the game
    game_words = []
    for word_obj in words_query:
        game_words.append({
            'id': word_obj.id,
            'word': word_obj.word.upper(),  # Uppercase for hangman
            'translation': word_obj.perevod,
            'definition': getattr(word_obj, 'definition', ''),
            'example': getattr(word_obj, 'example', '')
        })

    return render_template('game_hangman_improved.html',
                           words_data=game_words,
                           class_name=class_name,
                           unit_name=unit_name,
                           module_name=module_name,
                           timer_duration=timer_duration,
                           enable_stopwatch=enable_stopwatch,
                           difficulty=difficulty,
                           game_mode=game_mode,
                           num_words=len(game_words))


@app.route('/test_details_data/<int:test_id>')
def test_details_data(test_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    user = db.session.get(User, session['user_id'])
    if not user or user.teacher != 'yes': # Only teachers should access this live data endpoint
        return jsonify({'error': 'Forbidden for non-teachers'}), 403

    test = Test.query.get_or_404(test_id)
    if test.created_by != user.id:
        return jsonify({'error': 'Forbidden, not test creator'}), 403

    students_in_class = User.query.filter_by(class_number=test.classs, teacher='no').all()
    total_students_in_class = len(students_in_class)
    all_results_for_test = TestResult.query.filter(
        TestResult.test_id == test.id,
        TestResult.started_at >= test.created_at
    ).all()

    completed_students_details_json = []
    in_progress_students_details_json = []
    not_started_student_ids = {s.id for s in students_in_class}

    for result in all_results_for_test:
        student_user = db.session.get(User, result.user_id)
        if not student_user or student_user.teacher == 'yes':
            if student_user and result.user_id in not_started_student_ids:
                not_started_student_ids.remove(result.user_id)
            continue

        if result.user_id in not_started_student_ids:
            not_started_student_ids.remove(result.user_id)
        
        student_data = {
            'id': student_user.id,
            'fio': student_user.fio,
            'nick': student_user.nick,
            'result_id': result.id
        }

        if result.completed_at:
            student_data.update({
                'completed_at_iso': result.completed_at.isoformat() + "Z" if result.completed_at else None,
                'score': result.score,
                'correct_answers': result.correct_answers,
                'total_questions': result.total_questions,
                'time_taken_display': format_time_taken(result.time_taken),
                'time_taken_minutes': result.time_taken
            })
            completed_students_details_json.append(student_data)
        else: # In progress
            item_data_for_template = {
                'remaining_time_display': "Без ограничений",
                'has_time_limit': False,
                'end_time_utc_iso': None,
                'started_at_iso': result.started_at.isoformat() + "Z" if result.started_at else None
            }
            if test.time_limit and test.time_limit > 0 and result.started_at:
                end_time_utc = result.started_at + timedelta(minutes=test.time_limit)
                now_utc = datetime.utcnow()
                item_data_for_template['has_time_limit'] = True
                item_data_for_template['end_time_utc_iso'] = end_time_utc.isoformat() + "Z"
                if now_utc < end_time_utc:
                    remaining_delta = end_time_utc - now_utc
                    hours, remainder = divmod(remaining_delta.total_seconds(), 3600)
                    minutes, seconds_float = divmod(remainder, 60)
                    seconds = int(seconds_float)
                    if hours > 0:
                        item_data_for_template['remaining_time_display'] = f"{int(hours)}h {int(minutes)}m {seconds}s left"
                    else:
                        item_data_for_template['remaining_time_display'] = f"{int(minutes)}m {seconds}s left"
                else:
                    item_data_for_template['remaining_time_display'] = "Время вышло"
            student_data.update(item_data_for_template)
            in_progress_students_details_json.append(student_data)

    not_started_students_json = []
    for uid in not_started_student_ids:
        s_user = db.session.get(User, uid)
        if s_user:
            not_started_students_json.append({'id': s_user.id, 'fio': s_user.fio, 'nick': s_user.nick})
    
    completed_count = len(completed_students_details_json)
    progress_percentage = (completed_count / total_students_in_class * 100) if total_students_in_class > 0 else 0

    data_to_return = {
        'test_id': test.id,
        'test_title': test.title,
        'is_active': test.is_active,
        'total_students_in_class': total_students_in_class,
        'completed_students_count': completed_count,
        'in_progress_students_count': len(in_progress_students_details_json),
        'not_started_students_count': len(not_started_students_json),
        'progress_percentage': round(progress_percentage, 2),
        'completed_students': completed_students_details_json,
        'in_progress_students': in_progress_students_details_json,
        'not_started_students': not_started_students_json,
        'urls': { # For constructing links in JS if needed
            'test_results_base': url_for('test_results', test_id=test.id, result_id=0)[:-1] # remove trailing 0
        }
    }
    return jsonify(data_to_return)

@app.route('/games/flashcards/update_review', methods=['POST'])
def update_flashcard_review():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized', 'success': False}), 401

    data = request.get_json()
    word_id = data.get('word_id')
    quality = data.get('quality') # 0: Again, 1: Hard, 2: Good, 3: Easy

    if word_id is None or quality is None:
        return jsonify({'error': 'Missing word_id or quality', 'success': False}), 400

    try:
        quality = int(quality)
        word_id = int(word_id)
    except ValueError:
        return jsonify({'error': 'Invalid word_id or quality format', 'success': False}), 400

    user_id = session['user_id']
    review_item = UserWordReview.query.filter_by(user_id=user_id, word_id=word_id).first()

    if not review_item:
        review_item = UserWordReview(user_id=user_id, word_id=word_id)
        db.session.add(review_item)
        # For a new card, initial interval is often 1 day for "Good", or more for "Easy"
        # If "Again" or "Hard" on a new card, it might stay at 0 or 1 day.
        # Let's initialize with values that will be updated by the logic below.

    # Simplified SM-2 like logic
    # q (quality): 0-Again, 1-Hard, 2-Good, 3-Easy
    # EF (ease factor): Default 2.5. Min 1.3.
    # I(n) (interval after nth repetition):
    # I(1) = 1 day
    # I(2) = 6 days
    # For n > 2, I(n) = I(n-1) * EF

    if quality < 2: # Again (0) or Hard (1)
        review_item.interval_days = 1 # Reset or set to a short interval
        # For "Again", some might reset EF, but simplified SM-2 often just resets interval
        if quality == 0: # Strong "Again" - might penalize EF slightly
             review_item.ease_factor = max(1.3, review_item.ease_factor - 0.2)
        elif quality == 1: # "Hard" - penalize EF less
             review_item.ease_factor = max(1.3, review_item.ease_factor - 0.15)

    elif quality == 2: # Good
        if review_item.interval_days == 0: # First time seeing or after reset
            review_item.interval_days = 1
        elif review_item.interval_days == 1:
             review_item.interval_days = 6
        else:
            review_item.interval_days = round(review_item.interval_days * review_item.ease_factor)
        # EF is not changed for "Good" in basic SM-2 after initial setting
        # review_item.ease_factor remains same or small adjustment: ef = ef - 0.0 + 0.1 ....
        # No change to EF on "Good" after initial setting is common.

    elif quality == 3: # Easy
        if review_item.interval_days == 0:
            review_item.interval_days = 4 # Start with a longer interval for "Easy" new cards
        elif review_item.interval_days == 1:
             review_item.interval_days = 10 # Jump if it was a short interval
        else:
            review_item.interval_days = round(review_item.interval_days * review_item.ease_factor * 1.3) # Boost for easy
        review_item.ease_factor = min(3.0, review_item.ease_factor + 0.15) # Increase EF for "Easy"

    # Cap interval to avoid excessively long periods (e.g., 1 year)
    review_item.interval_days = min(review_item.interval_days, 365)


    review_item.next_review_at = datetime.utcnow() + timedelta(days=review_item.interval_days)
    review_item.last_reviewed_at = datetime.utcnow()

    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'next_review_in_days': review_item.interval_days,
            'next_review_date': review_item.next_review_at.isoformat(),
            'ease_factor': review_item.ease_factor
        })
    except Exception as e:
        db.session.rollback()
        # Log the error e
        return jsonify({'error': 'Database commit failed', 'details': str(e), 'success': False}), 500

# API для сохранения промежуточных результатов теста
@app.route('/api/test/<int:test_id>/save_progress', methods=['POST'])
def save_test_progress(test_id):
    """Сохраняет промежуточные ответы пользователя во время прохождения теста"""
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    
    user = db.session.get(User, session['user_id'])
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 401
    
    # Получаем активный тест-результат
    test_result = TestResult.query.filter_by(
        test_id=test_id,
        user_id=user.id,
        completed_at=None
    ).first()
    
    if not test_result:
        return jsonify({'error': 'Активный тест не найден'}), 404
    
    try:
        data = request.get_json()
        if not data or 'answers' not in data:
            return jsonify({'error': 'Неверный формат данных'}), 400
        
        # Сохраняем или обновляем прогресс для каждого ответа
        for answer_data in data['answers']:
            test_word_id = answer_data.get('test_word_id')
            user_answer = answer_data.get('user_answer', '')
            
            if not test_word_id:
                continue
                
            # Проверяем, что test_word принадлежит этому тесту
            test_word = TestWord.query.filter_by(id=test_word_id, test_id=test_id).first()
            if not test_word:
                continue
            
            # Ищем существующую запись прогресса
            progress = TestProgress.query.filter_by(
                test_result_id=test_result.id,
                test_word_id=test_word_id
            ).first()
            
            if progress:
                # Обновляем существующую запись
                progress.user_answer = json.dumps(user_answer) if isinstance(user_answer, (dict, list)) else str(user_answer)
                progress.last_updated = datetime.utcnow()
            else:
                # Создаем новую запись
                progress = TestProgress(
                    test_result_id=test_result.id,
                    test_word_id=test_word_id,
                    user_answer=json.dumps(user_answer) if isinstance(user_answer, (dict, list)) else str(user_answer)
                )
                db.session.add(progress)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Прогресс сохранен'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка сохранения: {str(e)}'}), 500

@app.route('/api/test/<int:test_id>/load_progress', methods=['GET'])
def load_test_progress(test_id):
    """Загружает сохраненные промежуточные ответы пользователя"""
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    
    user = db.session.get(User, session['user_id'])
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 401
    
    # Получаем активный тест-результат
    test_result = TestResult.query.filter_by(
        test_id=test_id,
        user_id=user.id,
        completed_at=None
    ).first()
    
    if not test_result:
        return jsonify({'progress': {}})
    
    try:
        # Получаем все сохраненные ответы
        progress_entries = TestProgress.query.filter_by(
            test_result_id=test_result.id
        ).all()
        
        progress_data = {}
        for entry in progress_entries:
            try:
                # Пытаемся распарсить JSON, если не получается - используем как строку
                user_answer = json.loads(entry.user_answer) if entry.user_answer else ''
            except (json.JSONDecodeError, TypeError):
                user_answer = entry.user_answer or ''
            
            progress_data[str(entry.test_word_id)] = user_answer
        
        return jsonify({'progress': progress_data})
        
    except Exception as e:
        return jsonify({'error': f'Ошибка загрузки: {str(e)}'}), 500

# ==================== УПРАВЛЕНИЕ ТЕКСТОВЫМ КОНТЕНТОМ ====================

@app.route('/text_contents')
@require_login
@require_teacher
def text_contents():
    """Список всех текстовых контентов"""
    user = db.session.get(User, session['user_id'])
    
    # Получаем все текстовые контенты, созданные текущим пользователем
    contents = db.session.execute(
        db.select(TextContent).where(
            TextContent.created_by == user.id,
            TextContent.is_active == True
        ).order_by(TextContent.created_at.desc())
    ).scalars().all()
    
    return render_template('text_contents.html', contents=contents, user=user)

@app.route('/create_text_content', methods=['GET', 'POST'])
@require_login
@require_teacher
def create_text_content():
    """Создание нового текстового контента"""
    user = db.session.get(User, session['user_id'])
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        classs = request.form.get('class', '').strip()
        unit = request.form.get('unit', '').strip()
        module = request.form.get('module', '').strip()
        
        # Валидация
        if not title:
            flash('Название текста обязательно', 'error')
            return render_template('create_text_content.html', user=user)
        
        if not content or len(content) < 50:
            flash('Текст должен содержать не менее 50 символов', 'error')
            return render_template('create_text_content.html', user=user)
        
        if not classs:
            flash('Класс обязателен', 'error')
            return render_template('create_text_content.html', user=user)
        
        # Создаем новый текстовый контент
        new_content = TextContent(
            title=title,
            content=content,
            classs=classs,
            unit=unit if unit else None,
            module=module if module else None,
            created_by=user.id
        )
        
        try:
            db.session.add(new_content)
            db.session.commit()
            flash('Текстовый контент успешно создан!', 'success')
            return redirect(url_for('edit_text_questions', content_id=new_content.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании текстового контента: {str(e)}', 'error')
    
    return render_template('create_text_content.html', user=user)

@app.route('/edit_text_content/<int:content_id>', methods=['GET', 'POST'])
@require_login
@require_teacher
def edit_text_content(content_id):
    """Редактирование текстового контента"""
    user = db.session.get(User, session['user_id'])
    content = db.session.get(TextContent, content_id)
    
    if not content or content.created_by != user.id:
        flash('Текстовый контент не найден', 'error')
        return redirect(url_for('text_contents'))
    
    if request.method == 'POST':
        content.title = request.form.get('title', '').strip()
        content.content = request.form.get('content', '').strip()
        content.classs = request.form.get('class', '').strip()
        content.unit = request.form.get('unit', '').strip()
        content.module = request.form.get('module', '').strip()
        
        # Валидация
        if not content.title:
            flash('Название текста обязательно', 'error')
            return render_template('edit_text_content.html', content=content, user=user)
        
        if not content.content or len(content.content) < 50:
            flash('Текст должен содержать не менее 50 символов', 'error')
            return render_template('edit_text_content.html', content=content, user=user)
        
        if not content.classs:
            flash('Класс обязателен', 'error')
            return render_template('edit_text_content.html', content=content, user=user)
        
        try:
            db.session.commit()
            flash('Текстовый контент успешно обновлен!', 'success')
            return redirect(url_for('text_contents'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении текстового контента: {str(e)}', 'error')
    
    return render_template('edit_text_content.html', content=content, user=user)

@app.route('/edit_text_questions/<int:content_id>')
@require_login
@require_teacher
def edit_text_questions(content_id):
    """Редактирование вопросов к тексту"""
    user = db.session.get(User, session['user_id'])
    content = db.session.get(TextContent, content_id)
    
    if not content or content.created_by != user.id:
        flash('Текстовый контент не найден', 'error')
        return redirect(url_for('text_contents'))
    
    # Получаем все вопросы для данного текста
    questions = db.session.execute(
        db.select(TextQuestion).where(
            TextQuestion.text_content_id == content_id
        ).order_by(TextQuestion.order_number)
    ).scalars().all()
    
    return render_template('edit_text_questions.html', content=content, questions=questions, user=user)

@app.route('/add_text_question/<int:content_id>', methods=['POST'])
@require_login
@require_teacher
def add_text_question(content_id):
    """Добавление вопроса к тексту"""
    user = db.session.get(User, session['user_id'])
    content = db.session.get(TextContent, content_id)
    
    if not content or content.created_by != user.id:
        flash('Текстовый контент не найден', 'error')
        return redirect(url_for('text_contents'))
    
    question_text = request.form.get('question', '').strip()
    question_type = request.form.get('question_type', '').strip()
    correct_answer = request.form.get('correct_answer', '').strip()
    points = int(request.form.get('points', 1))
    
    # Валидация
    if not question_text:
        flash('Текст вопроса обязателен', 'error')
        return redirect(url_for('edit_text_questions', content_id=content_id))
    
    if not question_type:
        flash('Тип вопроса обязателен', 'error')
        return redirect(url_for('edit_text_questions', content_id=content_id))
    
    if not correct_answer:
        flash('Правильный ответ обязателен', 'error')
        return redirect(url_for('edit_text_questions', content_id=content_id))
    
    # Получаем следующий порядковый номер
    max_order = db.session.execute(
        db.select(db.func.max(TextQuestion.order_number)).where(
            TextQuestion.text_content_id == content_id
        )
    ).scalar() or 0
    
    # Обработка вариантов ответов для multiple_choice и multiple_select
    options = None
    
    if question_type in ['multiple_choice', 'multiple_select']:
        option1 = request.form.get('option1', '').strip()
        option2 = request.form.get('option2', '').strip()
        option3 = request.form.get('option3', '').strip()
        option4 = request.form.get('option4', '').strip()
        
        options_list = [opt for opt in [option1, option2, option3, option4] if opt]
        if len(options_list) < 2:
            flash('Для вопроса с выбором ответа нужно минимум 2 варианта', 'error')
            return redirect(url_for('edit_text_questions', content_id=content_id))
        
        options = json.dumps(options_list, ensure_ascii=False)
        
        # Для множественного выбора проверяем правильный ответ
        if question_type == 'multiple_select':
            # Проверяем, что правильный ответ - это JSON массив
            try:
                correct_answers = json.loads(correct_answer)
                if not isinstance(correct_answers, list) or len(correct_answers) == 0:
                    flash('Для вопроса с множественным выбором нужно выбрать хотя бы один правильный ответ', 'error')
                    return redirect(url_for('edit_text_questions', content_id=content_id))
            except json.JSONDecodeError:
                flash('Ошибка в формате правильных ответов для множественного выбора', 'error')
                return redirect(url_for('edit_text_questions', content_id=content_id))
    
    # Создаем новый вопрос
    new_question = TextQuestion(
        text_content_id=content_id,
        question=question_text,
        question_type=question_type,
        options=options,
        correct_answer=correct_answer,
        points=points,
        order_number=max_order + 1
    )
    
    try:
        db.session.add(new_question)
        db.session.commit()
        flash('Вопрос успешно добавлен!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении вопроса: {str(e)}', 'error')
    
    return redirect(url_for('edit_text_questions', content_id=content_id))

@app.route('/delete_text_question/<int:question_id>', methods=['POST'])
@require_login
@require_teacher
def delete_text_question(question_id):
    """Удаление вопроса"""
    user = db.session.get(User, session['user_id'])
    question = db.session.get(TextQuestion, question_id)
    
    if not question or question.text_content.created_by != user.id:
        flash('Вопрос не найден', 'error')
        return redirect(url_for('text_contents'))
    
    content_id = question.text_content_id
    
    try:
        db.session.delete(question)
        db.session.commit()
        flash('Вопрос успешно удален!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении вопроса: {str(e)}', 'error')
    
    return redirect(url_for('edit_text_questions', content_id=content_id))

@app.route('/create_test_from_text/<int:content_id>')
@require_login
@require_teacher
def create_test_from_text(content_id):
    """Создание теста на основе текстового контента"""
    user = db.session.get(User, session['user_id'])
    content = db.session.get(TextContent, content_id)
    
    if not content or content.created_by != user.id:
        flash('Текстовый контент не найден', 'error')
        return redirect(url_for('text_contents'))
    
    # Проверяем, есть ли вопросы
    questions_count = db.session.execute(
        db.select(db.func.count(TextQuestion.id)).where(
            TextQuestion.text_content_id == content_id
        )
    ).scalar()
    
    if questions_count == 0:
        flash('Сначала добавьте вопросы к тексту', 'error')
        return redirect(url_for('edit_text_questions', content_id=content_id))
    
    # Генерируем уникальную ссылку для теста
    test_link = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    while db.session.execute(db.select(Test).where(Test.link == test_link)).scalar():
        test_link = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    
    # Создаем новый тест
    new_test = Test(
        title=f"Тест по тексту: {content.title}",
        classs=content.classs,
        unit=content.unit or "N/A",
        module=content.module or "N/A",
        type='text_based',
        link=test_link,
        created_by=user.id,
        word_order='sequential',
        text_content_id=content_id
    )
    
    try:
        db.session.add(new_test)
        db.session.commit()
        flash('Тест успешно создан!', 'success')
        return redirect(url_for('test_details', test_id=new_test.id))
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при создании теста: {str(e)}', 'error')
        return redirect(url_for('text_contents'))

# Blueprints are already registered at the top of the file
# app.register_blueprint(tests_bp, url_prefix='/tests') # Example for future
# app.register_blueprint(games_bp, url_prefix='/games') # Example for future

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # Add sample sentences if none exist
        if Sentence.query.count() == 0:
            sample_sentences = [
                Sentence(text="This is a simple sentence.", translation="Это простое предложение.", classs="5", unit="1", module="Greetings"),
                Sentence(text="The cat sleeps on the mat.", translation="Кошка спит на коврике.", classs="5", unit="1", module="Greetings"),
                Sentence(text="I like to learn English.", translation="Мне нравится учить английский.", classs="5", unit="1", module="School"),
                Sentence(text="She reads a book every day.", translation="Она читает книгу каждый день.", classs="6", unit="2", module="Hobbies"),
                Sentence(text="They play football in the park.", translation="Они играют в футбол в парке.", classs="6", unit="2", module="Hobbies")
            ]
            db.session.bulk_save_objects(sample_sentences)
            db.session.commit()
            print("Added sample sentences.")
        print("Database tables created (or already exist). Running test.py...") # Optional: for logging
        try:
            subprocess.run(["python", "test.py"], check=True, capture_output=True, text=True)
            print("test.py executed successfully.") # Optional: for logging
        except subprocess.CalledProcessError as e:
            print(f"Error running test.py: {e}") # Optional: for logging
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
            # Decide if you want to exit or continue if test.py fails
            # For now, it will continue to app.run()
    app.run("0.0.0.0", debug=True, port=1800)
