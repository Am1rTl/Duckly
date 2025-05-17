from markupsafe import escape
from flask import Flask, jsonify, request, render_template, redirect, url_for, flash, make_response, session
from flask_sqlalchemy import SQLAlchemy
import base64 as bs64
import time
import sqlite3
import random
import string
from datetime import datetime
import json



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your-super-secret-key-12345'  # Added secret key for session management
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    fio = db.Column(db.String, nullable=False)
    nick = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    secret_key = db.Column(db.String, nullable=False)
    teacher = db.Column(db.String, nullable=True)
    class_number = db.Column(db.String, nullable=True)  # Added for student class

class Word(db.Model):
    __tablename__ = 'words'
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String, nullable=False)
    perevod = db.Column(db.String, nullable=False)
    classs = db.Column('class', db.String, nullable=False)
    unit = db.Column(db.String, nullable=False)
    module = db.Column(db.String, nullable=False)

class Test(db.Model):
    __tablename__ = 'tests'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    classs = db.Column('class', db.String, nullable=False)
    unit = db.Column(db.String, nullable=True, default="N/A")
    module = db.Column(db.String, nullable=True, default="N/A")
    type = db.Column(db.String, nullable=False)  # dictation, add_letter, true_false, multiple_choice_single, multiple_choice_multiple, fill_word
    link = db.Column(db.String, unique=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    time_limit = db.Column(db.Integer, nullable=True)  # Time limit in minutes
    word_order = db.Column(db.String, nullable=False)  # 'random' or 'sequential'
    word_count = db.Column(db.Integer, nullable=True)  # For random order
    test_mode = db.Column(db.String, nullable=True)  # 'random_letters' or 'manual_letters' for add_letter type
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    test_words = db.relationship('TestWord', backref='test', lazy=True)

class TestWord(db.Model):
    __tablename__ = 'test_words'
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id'), nullable=False)
    word = db.Column(db.String, nullable=False)
    perevod = db.Column(db.String, nullable=False)
    missing_letters = db.Column(db.String, nullable=True)  # For add_letter type tests
    options = db.Column(db.String, nullable=True)  # For multiple choice tests (JSON string)
    correct_answer = db.Column(db.String, nullable=False)
    word_order = db.Column(db.Integer, nullable=False)  # To maintain word order in sequential tests

class TestResult(db.Model):
    __tablename__ = 'test_results'
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False, default=0)
    correct_answers = db.Column(db.Integer, nullable=False, default=0)
    total_questions = db.Column(db.Integer, nullable=False, default=0)
    time_taken = db.Column(db.Integer, nullable=False, default=0)  # in minutes
    started_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    completed_at = db.Column(db.DateTime, nullable=True)
    current_word_index = db.Column(db.Integer, default=0)  # Track progress
    answers = db.Column(db.String, nullable=True)  # JSON string of answers

    test = db.relationship('Test', backref=db.backref('results', lazy=True))
    user = db.relationship('User', backref=db.backref('test_results', lazy=True))
    test_answers = db.relationship('TestAnswer', backref='test_result', lazy=True, cascade='all, delete-orphan')

class TestAnswer(db.Model):
    __tablename__ = 'test_answers'
    id = db.Column(db.Integer, primary_key=True)
    test_result_id = db.Column(db.Integer, db.ForeignKey('test_results.id'), nullable=False)
    test_word_id = db.Column(db.Integer, db.ForeignKey('test_words.id'), nullable=False)
    user_answer = db.Column(db.String(255), nullable=True)
    is_correct = db.Column(db.Boolean, nullable=False, default=False)
    answered_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    test_word = db.relationship('TestWord', backref=db.backref('answers', lazy=True))



@app.route("/")
def index():
    return redirect('/hello', 302)

@app.route("/user/<name>")
def greet(name):
    return f"Hello, {name}!"

@app.route("/profile")
def profile():
    reqinnone = 0
    user = None
    for cookie_name in request.cookies:
        user_obj = User.query.filter_by(nick=cookie_name).first()
        if user_obj:
            secret_key = bs64.b64encode(str.encode(user_obj.nick + user_obj.password[:2])).decode("utf-8")
            if request.cookies.get(cookie_name) == secret_key:
                user = user_obj
                break
            elif request.cookies.get(cookie_name) is not None:
                res = make_response(redirect('hello', 302))
                res.set_cookie(cookie_name, request.cookies.get(cookie_name), max_age=0)
                return res
    if user is None:
        return redirect('/login', 302)
    return render_template('profile.html', nick=user.nick, fio=user.fio)


@app.route("/add_tests", methods=['POST', 'GET'])
def add_tests():
    if request.method == "POST":
        classs = request.form['classSelect']
        unit = request.form['unit']
        module = request.form['module']
        types = request.form['type']
        title = request.form.get('title', f'Тест {unit} - {module}')  # Добавляем заголовок
        times = str(time.time()).split(".")
        link = times[0]+times[1]
        new_test = Test(
            title=title,
            classs=classs,
            unit=unit,
            module=module,
            type=types,
            link=link,
            created_by=1,  # Временно используем ID 1 для тестового учителя
            is_active=True,
            word_order='random'
        )
        db.session.add(new_test)
        db.session.commit()
        return redirect('/tests', 302)
    else:
        # Get all available classes
        classes = [str(i) for i in range(1, 12)]
        return render_template("add_tests.html", classes=classes)

@app.route("/tests")
def tests():
    user = None
    for cookie_name in request.cookies:
        user_obj = User.query.filter_by(nick=cookie_name).first()
        if user_obj:
            secret_key = bs64.b64encode(str.encode(user_obj.nick + user_obj.password[:2])).decode("utf-8")
            if request.cookies.get(cookie_name) == secret_key:
                user = user_obj
                break
            elif request.cookies.get(cookie_name) is not None:
                res = make_response(redirect('hello', 302))
                res.set_cookie(cookie_name, request.cookies.get(cookie_name), max_age=0)
                return res
    if user is None:
        return redirect('/login', 302)

    show_archived = request.args.get('show_archived', 'false') == 'true'
    
    tests_data = []
    if user.teacher == 'yes':
        # Teachers see all tests they created
        tests_query = Test.query.filter_by(created_by=user.id, is_active=not show_archived).order_by(Test.created_at.desc()).all()
        for test_item in tests_query:
            students_in_class = User.query.filter_by(class_number=test_item.classs, teacher='no').count()
            completed_results = TestResult.query.filter_by(test_id=test_item.id, completed_at=None).count() # This should be completed_at IS NOT None
            
            # Corrected logic for completed_results
            completed_count = TestResult.query.filter(
                TestResult.test_id == test_item.id,
                TestResult.completed_at.isnot(None) # Check that completed_at is not NULL
            ).count()

            progress = 0
            if students_in_class > 0:
                progress = round((completed_count / students_in_class) * 100)
            
            tests_data.append({
                'test': test_item,
                'students_in_class': students_in_class,
                'completed_count': completed_count,
                'progress': progress
            })
    else:
        # Students see only tests for their class
        tests_query = Test.query.filter_by(classs=user.class_number, is_active=not show_archived).order_by(Test.created_at.desc()).all()
        # For students, we don't typically show progress bars of other students on the main list
        for test_item in tests_query:
            tests_data.append({
                'test': test_item,
                'students_in_class': 0, # Not relevant for student's direct view here
                'completed_count': 0, # Not relevant
                'progress': 0 # Not relevant
            })


    return render_template('tests.html', tests_data=tests_data, show_archived=show_archived, is_teacher=user.teacher == 'yes')

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

@app.route("/tests/<id>", methods=['GET', 'POST'])
def test_id(id):
    user = None
    for cookie_name in request.cookies:
        user_obj = User.query.filter_by(nick=cookie_name).first()
        if user_obj:
            secret_key = bs64.b64encode(str.encode(user_obj.nick + user_obj.password[:2])).decode("utf-8")
            if request.cookies.get(cookie_name) == secret_key:
                user = user_obj
                break
            elif request.cookies.get(cookie_name) is not None:
                res = make_response(redirect('hello', 302))
                res.set_cookie(cookie_name, request.cookies.get(cookie_name), max_age=0)
                return res
    if user is None:
        return redirect('/login', 302)

    test = Test.query.filter_by(link=id).first()
    if not test:
        return "Test not found", 404

    # Check if user has access to this test
    if user.teacher != 'yes' and test.classs != user.class_number:
        return "Access denied", 403

    # Check if test is active
    if not test.is_active and user.teacher != 'yes':
        return "This test is no longer active", 403

    # Get or create test result
    test_result = TestResult.query.filter_by(
        test_id=test.id,
        user_id=user.id,
        completed_at=None
    ).first()

    if request.method == 'POST':
        if not test_result:
            # Start new test
            test_result = TestResult(
                test_id=test.id,
                user_id=user.id,
                total_questions=len(test.test_words),
                started_at=datetime.utcnow()
            )
            db.session.add(test_result)
            db.session.commit()

        # Process answers
        answers = {}
        score = 0
        for word in test.test_words:
            answer = request.form.get(f'answer{word.id}', '').strip().lower()
            answers[str(word.id)] = answer

            if test.type == 'add_letter':
                # For add_letter type, check if the missing letters are correct
                missing_letters = word.missing_letters.split(',')
                correct_answer = ''.join(word.word[int(pos)-1] for pos in missing_letters)
                if answer == correct_answer.lower():
                    score += 1
            elif test.type == 'multiple_choice':
                # For multiple choice, check if the selected option matches the correct answer
                if answer == word.word.lower():
                    score += 1
            else:
                # For other types (dictation, true_or_false), check exact match
                if answer == word.word.lower():
                    score += 1

        # Update test result
        test_result.score = int((score / len(test.test_words)) * 100)
        test_result.correct_answers = score
        test_result.completed_at = datetime.utcnow()
        test_result.answers = json.dumps(answers)
        db.session.commit()

        return redirect(url_for('test_results', test_id=test.id, result_id=test_result.id))

    # GET request - show test
    if test.type == 'add_letter':
        words_list = []
        for word in test.test_words:
            word_text = word.word
            missing_letters = word.missing_letters.split(',')
            positions = [int(pos) - 1 for pos in missing_letters]
            word_with_gaps = list(word_text)
            for pos in positions:
                word_with_gaps[pos] = '_'
            words_list.append({
                'id': word.id,
                'word': ''.join(word_with_gaps),
                'perevod': word.perevod,
                'missing_letters': missing_letters
            })
        return render_template('test_add_letter.html', 
                             words=words_list, 
                             test_id=id,
                             test_result=test_result,
                             time_limit=test.time_limit)
    elif test.type == 'dictation':
        words_list = [(word.word, word.perevod) for word in test.test_words]
        return render_template('test_dictation.html', 
                             words=words_list, 
                             test_id=id,
                             test_result=test_result,
                             time_limit=test.time_limit)
    elif test.type == 'true_or_false':
        words_list = [(word.word, word.perevod) for word in test.test_words]
        return render_template('test_true_or_false.html', 
                             words=words_list, 
                             test_id=id,
                             test_result=test_result,
                             time_limit=test.time_limit)
    elif test.type == 'multiple_choice':
        words_list = []
        for word in test.test_words:
            options = word.options.split('|')
            words_list.append({
                'id': word.id,
                'word': word.word,
                'perevod': word.perevod,
                'options': options
            })
        return render_template('test_multiple_choice.html', 
                             words=words_list, 
                             test_id=id,
                             test_result=test_result,
                             time_limit=test.time_limit)
    else:
        return "Unknown test type", 400

@app.route("/edit_profile")
def edit_profile():
    user = None
    for cookie_name in request.cookies:
        user_obj = User.query.filter_by(nick=cookie_name).first()
        if user_obj:
            secret_key = bs64.b64encode(str.encode(user_obj.nick + user_obj.password[:2])).decode("utf-8")
            if request.cookies.get(cookie_name) == secret_key:
                user = user_obj
                break
            elif request.cookies.get(cookie_name) is not None:
                res = make_response(redirect('hello', 302))
                res.set_cookie(cookie_name, request.cookies.get(cookie_name), max_age=0)
                return res
    if user is None:
        return redirect('/login', 302)
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

@app.route("/add_words", methods=['POST', 'GET'])
def add_words():
    if request.method == "POST":
        class_val = request.form.get('classSelect')
        unit_val = request.form.get('unitSelect')
        module_val = request.form.get('moduleSelect')  # Changed from 'module'

        if class_val == 'add_new_class':
            classs = request.form.get('newClassInput', '').strip()
        else:
            classs = class_val

        if unit_val == 'add_new_unit':
            unit = request.form.get('newUnitInput', '').strip()
        else:
            unit = unit_val

        if module_val == 'add_new_module':
            module = request.form.get('newModuleInput', '').strip()
        else:
            module = module_val

        # Ensure classs, unit, and module are not None and provide defaults if necessary
        classs = classs if classs is not None else ""
        unit = unit if unit is not None else ""
        module = module if module is not None else ""

        words = []
        perevods = []

        for key, value in request.form.items():
            if key.startswith("word"):
                words.append(value)
            elif key.startswith("perevod"):
                perevods.append(value)

        for word, perevod in zip(words, perevods):
            new_word = Word(word=word, perevod=perevod, classs=classs, unit=unit, module=module)
            db.session.add(new_word)
        db.session.commit()
        return redirect('/words', 302)

    # GET method: query existing classes
    classes = [str(i) for i in range(1, 12)]
    return render_template("add_words.html", classes=classes)

@app.route("/get_units_for_class")
def get_units_for_class():
    class_name = request.args.get('class_name')
    if not class_name:
        return jsonify([])
    
    # Get unique units for the selected class
    units = db.session.query(Word.unit).filter(
        Word.classs == class_name
    ).distinct().all()
    
    return jsonify([unit[0] for unit in units])

@app.route("/get_modules_for_unit")
def get_modules_for_unit():
    class_name = request.args.get('class_name')
    unit_name = request.args.get('unit_name')
    
    if not class_name or not unit_name:
        return jsonify([])
    
    # Get unique modules for the selected class and unit
    modules = db.session.query(Word.module).filter(
        Word.classs == class_name,
        Word.unit == unit_name
    ).distinct().all()
    
    return jsonify([module[0] for module in modules])

@app.route('/words')
def words():
    words = Word.query.order_by(Word.classs).all()
    items = {}

    # Build items by class, unit, module
    for w in words:
        if w.classs not in items:
            items[w.classs] = {}
        if w.unit not in items[w.classs]:
            items[w.classs][w.unit] = {}
        if w.module not in items[w.classs][w.unit]:
            items[w.classs][w.unit][w.module] = []
        items[w.classs][w.unit][w.module].append([w.word, w.perevod])

    return render_template("words.html", items=items)

@app.route('/edit_word/<original_word_text>', methods=['GET', 'POST'])
def edit_word(original_word_text):
    # Параметры для идентификации оригинального слова (из URL GET запроса)
    original_class = request.args.get('class')
    original_unit = request.args.get('unit')
    original_module = request.args.get('module')
    
    # Находим объект слова для редактирования
    # Важно: Ищем по оригинальным значениям, переданным при открытии формы
    word_obj = Word.query.filter_by(
        word=original_word_text, 
        classs=original_class, 
        unit=original_unit, 
        module=original_module
    ).first()
    
    if not word_obj:
        flash("Слово для редактирования не найдено!", "error")
        return redirect(url_for('words'))

    if request.method == 'POST':
        # Получаем данные из формы
        new_word_text = request.form.get('word')
        new_perevod = request.form.get('perevod')
        
        selected_class = request.form.get('classSelect')
        selected_unit_option = request.form.get('unitSelect')
        selected_module_option = request.form.get('moduleSelect')

        new_class = selected_class # Класс всегда выбирается из существующих

        if selected_unit_option == 'add_new_unit':
            new_unit = request.form.get('newUnitInput', '').strip()
            if not new_unit: # Если поле нового юнита пустое, но выбрано "добавить"
                flash("Необходимо указать название нового юнита.", "error")
                # Перезагружаем форму с уже введенными данными
                all_classes = [str(i) for i in range(1, 12)]
                return render_template('edit_word.html', 
                                   word={'word': new_word_text, 'perevod': new_perevod, 'classs': new_class, 'unit': word_obj.unit, 'module': word_obj.module},
                                   classs=original_class, 
                                   unit=original_unit, 
                                   module=original_module, 
                                   all_classes=all_classes,
                                   error="Необходимо указать название нового юнита.")
        else:
            new_unit = selected_unit_option

        if selected_module_option == 'add_new_module':
            new_module = request.form.get('newModuleInput', '').strip()
            # Если new_module пустой, это означает "нет модуля" или пользователь хочет создать пустой модуль
        elif selected_module_option == "": # Опция "--- Нет модуля ---"
             new_module = "" 
        else:
            new_module = selected_module_option
        
        # Валидация, что класс и юнит не пустые, если они обязательны
        if not new_class:
            flash("Класс не может быть пустым.", "error")
            # Снова рендерим шаблон с ошибкой и данными
            all_classes = [str(i) for i in range(1, 12)]
            return render_template('edit_word.html', 
                               word={'word': new_word_text, 'perevod': new_perevod, 'classs': new_class, 'unit': new_unit, 'module': new_module},
                               classs=original_class, unit=original_unit, module=original_module, 
                               all_classes=all_classes, error="Класс не может быть пустым.")
        if not new_unit:
            flash("Юнит не может быть пустым.", "error")
            # Снова рендерим шаблон с ошибкой и данными
            all_classes = [str(i) for i in range(1, 12)]
            return render_template('edit_word.html', 
                               word={'word': new_word_text, 'perevod': new_perevod, 'classs': new_class, 'unit': new_unit, 'module': new_module},
                               classs=original_class, unit=original_unit, module=original_module, 
                               all_classes=all_classes, error="Юнит не может быть пустым.")

        # Обновляем объект слова
        word_obj.word = new_word_text
        word_obj.perevod = new_perevod
        word_obj.classs = new_class
        word_obj.unit = new_unit
        word_obj.module = new_module if new_module is not None else "" # Гарантируем, что модуль не None

        try:
            db.session.commit()
            flash("Слово успешно обновлено!", "success")
            # Редирект на страницу слов с параметрами, чтобы выделить или отфильтровать измененное слово
            return redirect(url_for('words', cl=word_obj.classs, un=word_obj.unit, mo=word_obj.module))
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при обновлении слова: {str(e)}", "error")
            # Снова рендерим шаблон с ошибкой и данными
            all_classes = [str(i) for i in range(1, 12)]
            return render_template('edit_word.html', 
                               word=word_obj, # Передаем измененный, но не сохраненный word_obj
                               classs=original_class, unit=original_unit, module=original_module, 
                               all_classes=all_classes, error=f"Ошибка БД: {str(e)}")

    # GET-запрос: отображение формы
    all_classes = [str(i) for i in range(1, 12)]
    
    # Передаем оригинальные значения class, unit, module для корректной работы JS при загрузке
    return render_template('edit_word.html', 
                       word=word_obj, 
                       classs=word_obj.classs,  # Используем актуальные данные из word_obj
                       unit=word_obj.unit,    # для предзаполнения и JS
                       module=word_obj.module, 
                       all_classes=all_classes)

@app.route('/delete_word/<word>', methods=['POST'])
def delete_word(word):
    # Get the data from the JSON request
    data = request.get_json()
    classs = data.get('class')
    unit = data.get('unit')
    module = data.get('module')
    
    # Find the word in the database
    word_obj = Word.query.filter_by(word=word, classs=classs, unit=unit, module=module).first()
    
    if not word_obj:
        return jsonify({'success': False, 'error': 'Word not found'}), 404
    
    # Delete the word
    db.session.delete(word_obj)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/login', methods=['POST', 'GET'])
def login():
    error = None
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        # Check for special teacher credentials
        if username == 'teacher' and password == 'teacher':
            # Check if teacher user exists, if not create it
            teacher = User.query.filter_by(nick='teacher').first()
            if not teacher:
                teacher = User(
                    fio='Teacher',
                    nick='teacher',
                    password='teacher',
                    secret_key=bs64.b64encode(str.encode('teacher' + 'teacher'[:2])).decode("utf-8"),
                    teacher='yes'
                )
                db.session.add(teacher)
                db.session.commit()
            
            secret_key = bs64.b64encode(str.encode('teacher' + 'teacher'[:2])).decode("utf-8")
            resp = make_response(redirect('hello', 302))
            resp.set_cookie('teacher', secret_key, 60*60*24*15)
            return resp

        # Regular user login
        user = User.query.filter_by(nick=username, password=password).first()
        if user:
            secret_key = bs64.b64encode(str.encode(username + password[:2])).decode("utf-8")
            resp = make_response(redirect('hello', 302))
            resp.set_cookie(username, secret_key, 60*60*24*15)
            return resp
        else:
            error = 'Invalid username/password'

    return render_template('login.html', error=error)

@app.route("/logout")
def logout():
    username = None
    for cookie_name in request.cookies:
        if User.query.filter_by(nick=cookie_name).first():
            username = cookie_name
            break
    if username:
        res = make_response(redirect('/login', 302))
        res.set_cookie(username, '', expires=0)
        return res
    else:
        return redirect('/login', 302)

@app.route('/registration', methods=['POST', 'GET'])
def registration():
    error = None
    if request.method == 'POST':
        fio = request.form["fio"]
        username = request.form['username']
        password = request.form['password']
        class_number = request.form.get('class_number')

        if not class_number:
            error = "Please select a class"
            return render_template('registration.html', error=error, classes=[str(i) for i in range(1, 12)])

        secret_key = bs64.b64encode(str.encode(username + password[:2])).decode("utf-8")

        max_id = db.session.query(db.func.max(User.id)).scalar()
        if max_id is None:
            max_id = 0
        else:
            max_id += 1

        existing_user = User.query.filter_by(nick=username).first()

        fio_in_mass = fio.split(' ')
        if len(fio_in_mass) == 3:
            if existing_user is None:
                new_user = User(
                    fio=fio,
                    nick=username,
                    password=password,
                    secret_key=secret_key,
                    teacher='no',
                    class_number=class_number,
                    id=max_id
                )
                db.session.add(new_user)
                db.session.commit()
                resp = make_response(redirect('hello', 302))
                resp.set_cookie(username, secret_key, 60*60*24*15)
                return resp
            else:
                error = "Выбранный вами Username уже занят"
        else:
            error = "ФИО должно состоять из 3 слов"
    else:
        error = None

    classes = [str(i) for i in range(1, 12)]  # Classes 1-11
    return render_template('registration.html', error=error, classes=classes)

@app.route("/hello")
def hello():
    user = None
    for cookie_name in request.cookies:
        user_obj = User.query.filter_by(nick=cookie_name).first()
        if user_obj:
            secret_key = bs64.b64encode(str.encode(user_obj.nick + user_obj.password[:2])).decode("utf-8")
            if request.cookies.get(cookie_name) == secret_key:
                user = user_obj
                break
            elif request.cookies.get(cookie_name) is not None:
                res = make_response(redirect('hello', 302))
                res.set_cookie(cookie_name, request.cookies.get(cookie_name), max_age=0)
                return res
    if user is None:
        return redirect('/login', 302)

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

@app.route("/edit_word")
def edit_word_form():
    # Get word details from URL parameters
    word = request.args.get("word")
    perevod = request.args.get("perevod")
    classs = request.args.get("class")
    unit = request.args.get("unit")
    
    # Find the word by its attributes
    word_to_edit = db.session.query(Word).filter_by(
        word=word,
        perevod=perevod,
        classs=classs,
        unit=unit
    ).first()
    
    if not word_to_edit:
        flash("Word not found!", "error")
        return redirect(url_for('words'))

    all_classes = [str(i) for i in range(1, 12)] # Assuming classes are 1-11
    # Units and modules will be loaded dynamically by JS
    # The word_to_edit object contains current class, unit, module for pre-selection
    return render_template("edit_word.html", word=word_to_edit, all_classes=all_classes)

@app.route("/update_word", methods=["POST"])
def update_word():
    word_id = request.form.get("word_id")
    word_to_update = Word.query.get(word_id)

    if not word_to_update:
        flash("Word not found for update!", "error")
        return redirect(url_for('words'))

    # Get new values, handling 'add_new_...' for unit and module
    new_class_val = request.form.get('classSelect')
    new_unit_val = request.form.get('unitSelect')
    new_module_val = request.form.get('moduleSelect')

    word_to_update.classs = new_class_val # Assuming classSelect directly provides the class

    if new_unit_val == 'add_new_unit':
        word_to_update.unit = request.form.get('newUnitInput')
    else:
        word_to_update.unit = new_unit_val

    if new_module_val == 'add_new_module':
        word_to_update.module = request.form.get('newModuleInput')
    else:
        word_to_update.module = new_module_val
    
    word_to_update.word = request.form.get("word")
    word_to_update.perevod = request.form.get("perevod")

    try:
        db.session.commit()
        flash("Word updated successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating word: {str(e)}", "error")

    return redirect(url_for('words', classs=word_to_update.classs, unit=word_to_update.unit, module=word_to_update.module))

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

    return redirect("/words")

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

    return redirect("/words")

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
        return redirect("/words")

    new_word = Word(word=word, perevod=perevod, classs=class_name, unit=unit_name, module=module_name)
    db.session.add(new_word)
    db.session.commit()

    return redirect("/words")



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
    user = None
    for cookie_name in request.cookies:
        user_obj = User.query.filter_by(nick=cookie_name).first()
        if user_obj:
            secret_key = bs64.b64encode(str.encode(user_obj.nick + user_obj.password[:2])).decode("utf-8")
            if request.cookies.get(cookie_name) == secret_key:
                user = user_obj
                break
    if user is None or user.teacher != 'yes':
        return redirect('/login', 302)

    if request.method == 'POST':
        test_type = request.form.get('test_type')
        class_number = request.form.get('class_number')
        title = request.form.get('title')
        
        time_limit_str = request.form.get('time_limit')
        time_limit = int(time_limit_str) if time_limit_str and int(time_limit_str) > 0 else None
        
        word_order = request.form.get('word_order')
        word_count_str = request.form.get('word_count')
        word_count = int(word_count_str) if word_count_str and word_order == 'random' else None
        
        test_mode = request.form.get('test_mode', 'random_letters')  # For add_letter type tests
        
        # Create new test
        new_test = Test(
            title=title,
            classs=class_number,
            # unit and module will be set later or use default "N/A"
            type=test_type,
            link=generate_test_link(),
            created_by=user.id,
            time_limit=time_limit,
            word_order=word_order,
            word_count=word_count,
            test_mode=test_mode
            # unit and module will default to "N/A" if not provided
        )
        db.session.add(new_test)
        db.session.commit()

        # Get words from selected modules
        words_data_source = [] # Using a new list to hold word data consistently
        selected_modules = request.form.getlist('modules[]')
        for module_identifier in selected_modules:
            class_num, unit, module_name = module_identifier.split('|')
            module_words_db = Word.query.filter_by(
                classs=class_num,
                unit=unit,
                module=module_name
            ).all()
            for mw in module_words_db:
                words_data_source.append({'word': mw.word, 'perevod': mw.perevod, 'source': 'module'})

        # Add custom words if provided
        custom_words_text = request.form.getlist('custom_words[]')
        custom_translations_text = request.form.getlist('custom_translations[]')
        for cw_text, ct_text in zip(custom_words_text, custom_translations_text):
            if cw_text and ct_text:  # Only add if both fields are filled
                words_data_source.append({
                    'word': cw_text,
                    'perevod': ct_text,
                    'source': 'custom'
                })

        # Shuffle words if word_order is 'random' before limiting by word_count
        if word_order == 'random':
            random.shuffle(words_data_source)
        
        # Limit word count if specified (especially for random order)
        if word_count is not None and word_count > 0 and len(words_data_source) > word_count:
            words_data_source = words_data_source[:word_count]
        elif word_order == 'sequential':
            # For sequential, word_count could still be used to limit the number of words from the start
            if word_count is not None and word_count > 0 and len(words_data_source) > word_count:
                 words_data_source = words_data_source[:word_count]


        # Create test words
        for idx, word_entry in enumerate(words_data_source):
            original_word_text = word_entry['word']
            original_translation = word_entry['perevod']
            
            # Initialize default values for TestWord fields
            # `word` field in TestWord: The primary question content shown to the student.
            # `perevod` field in TestWord: Supporting information, translation, or detailed prompt.
            # `correct_answer` field in TestWord: The definitive correct answer for grading.
            # `options` field in TestWord: For multiple choice, pipe-separated.
            # `missing_letters` field in TestWord: For add_letter, comma-separated 1-indexed positions.

            current_word_for_test_word_model = original_word_text # Default for what student interacts with
            prompt_for_test_word_model = original_translation   # Default for supporting info
            options_db = None
            missing_letters_positions_db = None
            correct_answer_for_db = original_word_text # Default correct answer

            if test_type == 'add_letter':
                prompt_for_test_word_model = original_translation
                if test_mode == 'random_letters':
                    if len(original_word_text) > 0:
                        num_letters_to_remove = random.randint(1, min(2, len(original_word_text)))
                        positions_zero_indexed = sorted(random.sample(range(len(original_word_text)), num_letters_to_remove))
                        
                        actual_missing_letters_list = [original_word_text[pos] for pos in positions_zero_indexed]
                        correct_answer_for_db = "".join(actual_missing_letters_list)
                        
                        word_with_gaps_list = list(original_word_text)
                        for pos in positions_zero_indexed:
                            word_with_gaps_list[pos] = '_'
                        current_word_for_test_word_model = "".join(word_with_gaps_list)
                        missing_letters_positions_db = ','.join(str(pos + 1) for pos in positions_zero_indexed)
                    else:
                        current_word_for_test_word_model = ""
                        correct_answer_for_db = ""
                        missing_letters_positions_db = ""
                else: # manual_letters - teacher needs to define these later. Store word as is for now.
                    # For manual mode, we store the word, and an editing step would be needed.
                    # Placeholder: remove first letter if word exists, for initial setup.
                    if len(original_word_text) > 0:
                        positions_zero_indexed = [0] 
                        actual_missing_letters_list = [original_word_text[pos] for pos in positions_zero_indexed]
                        correct_answer_for_db = "".join(actual_missing_letters_list)
                        word_with_gaps_list = list(original_word_text)
                        for pos in positions_zero_indexed:
                            word_with_gaps_list[pos] = '_'
                        current_word_for_test_word_model = "".join(word_with_gaps_list)
                        missing_letters_positions_db = ','.join(str(pos + 1) for pos in positions_zero_indexed)
                    else:
                        current_word_for_test_word_model = ""
                        correct_answer_for_db = ""
                        missing_letters_positions_db = ""
                        
            elif test_type == 'multiple_choice_single':
                # Question is the translation, options are words, one of which is correct.
                current_word_for_test_word_model = original_translation # This is the question: "What is the word for X?"
                prompt_for_test_word_model = "Выберите правильный перевод:" 
                correct_answer_for_db = original_word_text
                
                all_other_words_in_class = [w.word for w in Word.query.filter(Word.classs == class_number, Word.word != original_word_text).all()]
                num_wrong_options = 3
                
                wrong_options_list = []
                if len(all_other_words_in_class) >= num_wrong_options:
                    wrong_options_list = random.sample(all_other_words_in_class, num_wrong_options)
                else: 
                    wrong_options_list = all_other_words_in_class
                
                current_options_list_for_db = wrong_options_list + [original_word_text]
                random.shuffle(current_options_list_for_db)
                options_db = '|'.join(current_options_list_for_db)

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
                    current_word_for_test_word_model = f"{original_word_text} - {original_translation}" # The statement
                    correct_answer_for_db = "True" # Placeholder: assumes the direct pairing is true.
                
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

        db.session.commit()
        return redirect(url_for('test_details', test_id=new_test.id))

    # GET request - show form
    classes = [str(i) for i in range(1, 12)]
    return render_template('create_test.html', classes=classes)

@app.route("/test/<int:test_id>")
def test_details(test_id):
    user = None
    for cookie_name in request.cookies:
        user_obj = User.query.filter_by(nick=cookie_name).first()
        if user_obj:
            secret_key = bs64.b64encode(str.encode(user_obj.nick + user_obj.password[:2])).decode("utf-8")
            if request.cookies.get(cookie_name) == secret_key:
                user = user_obj
                break
    if user is None:
        return redirect('/login', 302)

    test = Test.query.get_or_404(test_id)
    
    # Check if user has access to this test
    if user.teacher != 'yes' and test.classs != user.class_number:
        # For students, redirect to the take_test view if they haven't completed it
        # or to results if they have. For now, redirecting to /tests if not their class.
        return redirect(url_for('tests')) # Simplified: if not teacher and not their class, back to tests list

    # Teacher's view or student viewing their own class's test details (if allowed by future logic)
    
    # Get all students in the test's class
    students_in_class = User.query.filter_by(class_number=test.classs, teacher='no').all()
    total_students_in_class = len(students_in_class)

    # Get all test results for this test
    all_results_for_test = TestResult.query.filter_by(test_id=test.id).all()

    completed_students_details = []
    in_progress_students_details = []
    not_started_student_ids = {s.id for s in students_in_class}

    for result in all_results_for_test:
        if result.user_id in not_started_student_ids:
            not_started_student_ids.remove(result.user_id)
        
        student_user = User.query.get(result.user_id)
        if not student_user: # Should not happen if DB is consistent
            continue

        if result.completed_at:
            completed_students_details.append({'user': student_user, 'result': result})
        else:
            in_progress_students_details.append({'user': student_user, 'result': result})

    not_started_students = [User.query.get(uid) for uid in not_started_student_ids]
    not_started_students = [s for s in not_started_students if s] # Filter out None if any ID was bad
    
    # Calculate overall progress for the bar
    completed_count = len(completed_students_details)
    progress_percentage = (completed_count / total_students_in_class * 100) if total_students_in_class > 0 else 0

    # Existing stats (can be refined or derived from the lists above)
    # total_students = User.query.filter_by(class_number=test.classs, teacher='no').count()
    # completed_students = len(results) # 'results' here was specifically for *a* user, not all.
    # in_progress = TestResult.query.filter_by(test_id=test_id, completed_at=None).count()
    
    return render_template('test_details.html',
                         test=test,
                         # results=results, # This was for a single result view, replaced by detailed lists
                         total_students_in_class=total_students_in_class,
                         completed_students_details=completed_students_details,
                         in_progress_students_details=in_progress_students_details,
                         not_started_students=not_started_students,
                         progress_percentage=progress_percentage,
                         # completed_students=completed_students, # Replaced by len(completed_students_details)
                         # in_progress_count=in_progress, # Replaced by len(in_progress_students_details)
                         is_teacher=user.teacher == 'yes')

@app.route("/test/<int:test_id>/archive", methods=['POST'])
def archive_test(test_id):
    user = None
    for cookie_name in request.cookies:
        user_obj = User.query.filter_by(nick=cookie_name).first()
        if user_obj:
            secret_key = bs64.b64encode(str.encode(user_obj.nick + user_obj.password[:2])).decode("utf-8")
            if request.cookies.get(cookie_name) == secret_key:
                user = user_obj
                break
    if user is None or user.teacher != 'yes':
        return redirect('/login', 302)

    test = Test.query.get_or_404(test_id)
    if test.created_by != user.id:
        return redirect('/tests', 302)

    test.is_active = False
    db.session.commit()
    return redirect(url_for('test_details', test_id=test_id))

@app.route('/take_test/<test_link>', methods=['GET', 'POST'])
def take_test(test_link):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    test = Test.query.filter_by(link=test_link).first_or_404()
    user = User.query.get(session['user_id'])

    # Check if user has access to this test
    if test.class_number != user.class_number:
        abort(403)

    # Check if user has already completed this test
    existing_result = TestResult.query.filter_by(
        test_id=test.id,
        user_id=user.id,
        completed_at=None
    ).first()

    if request.method == 'POST':
        # Start a new test
        if not existing_result:
            test_result = TestResult(
                test_id=test.id,
                user_id=user.id,
                total_questions=len(test.test_words)
            )
            db.session.add(test_result)
            db.session.commit()
            return jsonify({'success': True})

    # If there's an existing incomplete test, show it
    if existing_result:
        return render_template('take_test.html', test=test)

    # Otherwise, show the test start page
    return render_template('test_start.html', test=test)

@app.route('/submit_test/<int:test_id>', methods=['POST'])
def submit_test(test_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    test = Test.query.get_or_404(test_id)
    data = request.get_json()
    answers = data.get('answers', [])

    # Calculate score based on test type
    correct_answers = 0
    results = []
    total_questions = len(test.test_words)

    for i, word in enumerate(test.test_words):
        user_answer = answers[i] if i < len(answers) else None
        is_correct = False

        if test.type == 'add_letter':
            # For add_letter type, check if the missing letters are correct
            missing_letters = word.missing_letters.split(',')
            correct_answer = ''.join(word.word[int(pos)-1] for pos in missing_letters)
            is_correct = user_answer and user_answer.upper() == correct_answer.upper()
        elif test.type == 'multiple_choice':
            # For multiple choice, check if the selected option matches the correct answer
            is_correct = user_answer == word.word
        else:
            # For other types (dictation, true_or_false), check exact match
            is_correct = user_answer and user_answer.lower() == word.word.lower()

        if is_correct:
            correct_answers += 1

        results.append({
            'word': word.word,
            'translation': word.perevod,
            'user_answer': user_answer,
            'correct_answer': word.word,
            'is_correct': is_correct
        })

    # Calculate score percentage
    score = int((correct_answers / total_questions) * 100) if total_questions > 0 else 0

    # Save test result
    test_result = TestResult(
        test_id=test_id,
        user_id=session['user_id'],
        score=score,
        correct_answers=correct_answers,
        total_questions=total_questions,
        time_taken=test.time_limit if test.time_limit else 0,
        completed_at=datetime.utcnow()
    )
    db.session.add(test_result)

    # Save individual answers
    for i, result in enumerate(results):
        test_answer = TestAnswer(
            test_result=test_result,
            test_word_id=test.test_words[i].id,
            user_answer=result['user_answer'],
            is_correct=result['is_correct']
        )
        db.session.add(test_answer)

    db.session.commit()

    return jsonify({
        'success': True,
        'redirect': url_for('test_results', test_id=test_id, result_id=test_result.id)
    })

@app.route('/test_results/<int:test_id>/<int:result_id>')
def test_results(test_id, result_id):
    user = None
    for cookie_name in request.cookies:
        user_obj = User.query.filter_by(nick=cookie_name).first()
        if user_obj:
            secret_key = bs64.b64encode(str.encode(user_obj.nick + user_obj.password[:2])).decode("utf-8")
            if request.cookies.get(cookie_name) == secret_key:
                user = user_obj
                break
            elif request.cookies.get(cookie_name) is not None:
                res = make_response(redirect('hello', 302))
                res.set_cookie(cookie_name, request.cookies.get(cookie_name), max_age=0)
                return res
    if user is None:
        return redirect('/login', 302)

    test = Test.query.get_or_404(test_id)
    result = TestResult.query.get_or_404(result_id)

    # Verify that the result belongs to the current user
    if result.user_id != user.id:
        return redirect('/tests', 302)

    # Get detailed results
    results = []
    for answer in result.test_answers:
        results.append({
            'word': answer.test_word.word,
            'translation': answer.test_word.perevod,
            'user_answer': answer.user_answer,
            'correct_answer': answer.test_word.word,
            'is_correct': answer.is_correct
        })

    return render_template('test_results.html',
        test=test,
        score=result.score,
        correct_answers=result.correct_answers,
        total_questions=result.total_questions,
        time_taken=result.time_taken,
        incorrect_answers=result.total_questions - result.correct_answers,
        results=results
    )

@app.route("/games")
def games():
    user = None
    for cookie_name in request.cookies:
        user_obj = User.query.filter_by(nick=cookie_name).first()
        if user_obj:
            secret_key = bs64.b64encode(str.encode(user_obj.nick + user_obj.password[:2])).decode("utf-8")
            if request.cookies.get(cookie_name) == secret_key:
                user = user_obj
                break
            elif request.cookies.get(cookie_name) is not None:
                res = make_response(redirect('hello', 302))
                res.set_cookie(cookie_name, request.cookies.get(cookie_name), max_age=0)
                return res
    if user is None:
        return redirect('/login', 302)
    
    return render_template('games.html', is_teacher=user.teacher == 'yes')

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run("127.0.0.1", debug=True, port=1800)
