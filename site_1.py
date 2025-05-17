from markupsafe import escape
from flask import Flask, jsonify, request, render_template, redirect, url_for, flash, make_response, session
from flask_sqlalchemy import SQLAlchemy
import base64 as bs64
import time
import sqlite3
import random
import string
from datetime import datetime, timedelta
import json
import subprocess # Added to run external scripts



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
    
    # New fields for dictation test options
    dictation_word_source = db.Column(db.String, nullable=True) # e.g., "all_module", "selected_specific", "random_from_module"
    dictation_selected_words = db.Column(db.Text, nullable=True) # JSON list of word IDs for "selected_specific"

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
    user = None
    # Authentication check (copied from create_test)
    for cookie_name in request.cookies:
        user_obj = User.query.filter_by(nick=cookie_name).first()
        if user_obj:
            secret_key_expected = bs64.b64encode(str.encode(user_obj.nick + user_obj.password[:2])).decode("utf-8")
            if request.cookies.get(cookie_name) == secret_key_expected:
                user = user_obj
                break
    
    if user is None or user.teacher != 'yes':
        flash("Доступ запрещен. Пожалуйста, войдите как учитель.", "warning")
        return redirect(url_for('login'))

    if request.method == "POST":
        test_type = request.form.get('test_type')
        class_number = request.form.get('class_number') # from class_number select
        title = request.form.get('title')
        
        time_limit_str = request.form.get('time_limit')
        time_limit = int(time_limit_str) if time_limit_str and time_limit_str.isdigit() and int(time_limit_str) > 0 else None
        
        word_order_form = request.form.get('word_order', 'sequential') 
        
        word_count_form_str = request.form.get('word_count') # General word count
        word_count_form = int(word_count_form_str) if word_count_form_str and word_count_form_str.isdigit() and int(word_count_form_str) > 0 else None

        test_mode = request.form.get('test_mode', 'random_letters') if test_type == 'add_letter' else None
        
        new_test_params = {
            'title': title,
            'classs': class_number,
            'type': test_type,
            'link': generate_test_link(), # Assumes generate_test_link() is defined
            'created_by': user.id, # Use authenticated user's ID
            'time_limit': time_limit,
            'word_order': word_order_form,
            'test_mode': test_mode,
            'is_active': True # Default to active
        }

        words_data_source = [] # Holds {'id': ..., 'word': ..., 'perevod': ..., 'source': ...}

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
                    module_words_db = Word.query.filter_by(
                        classs=class_num,
                        unit=unit,
                        module=module_name
                    ).all()
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
        
        else: # For other test types (non-dictation)
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

        new_test = Test(**new_test_params)
        db.session.add(new_test)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при создании основной записи теста: {str(e)}", "error")
            classes_get = [str(i) for i in range(1, 12)]
            return render_template("add_tests.html", classes=classes_get, error_message=str(e))

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
                else: # manual_letters
                    if len(original_word_text) > 0:
                        positions_zero_indexed = [0]
                        actual_missing_letters_list = [original_word_text[pos] for pos in positions_zero_indexed]
                        correct_answer_for_db = "".join(actual_missing_letters_list)
                        word_with_gaps_list = list(original_word_text); word_with_gaps_list[0] = '_'
                        current_word_for_test_word_model = "".join(word_with_gaps_list)
                        missing_letters_positions_db = '1'
                    else:
                        current_word_for_test_word_model = ""; correct_answer_for_db = ""; missing_letters_positions_db = ""
                        
            elif test_type == 'multiple_choice_single':
                current_word_for_test_word_model = original_translation 
                prompt_for_test_word_model = "Выберите правильный перевод:" 
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

            elif test_type == 'true_false':
                if word_entry['source'] == 'custom':
                    current_word_for_test_word_model = original_word_text
                    correct_answer_for_db = original_translation if original_translation.lower() in ['true', 'false'] else "True"
                else:
                    current_word_for_test_word_model = f"{original_word_text} - {original_translation}"
                    correct_answer_for_db = "True"
                prompt_for_test_word_model = "Верно или неверно?"
                options_db = "True|False"
                
            elif test_type == 'fill_word':
                current_word_for_test_word_model = original_translation
                prompt_for_test_word_model = "Впишите соответствующее слово (оригинал):"
                correct_answer_for_db = original_word_text

            elif test_type == 'multiple_choice_multiple':
                current_word_for_test_word_model = original_translation
                prompt_for_test_word_model = "Выберите все подходящие варианты:"
                correct_answer_for_db = original_word_text # Placeholder
                all_other_words = [w.word for w in Word.query.filter(Word.classs == class_number, Word.word != original_word_text).limit(20).all()]
                num_options_total = 4
                num_wrong_options_needed = num_options_total - 1
                wrong_options_list = random.sample(all_other_words, min(num_wrong_options_needed, len(all_other_words)))
                current_options_list_for_db = wrong_options_list + [original_word_text]
                while len(current_options_list_for_db) < num_options_total:
                    current_options_list_for_db.append(f"Вариант {len(current_options_list_for_db)+1}")
                random.shuffle(current_options_list_for_db)
                options_db = '|'.join(current_options_list_for_db[:num_options_total])

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
        
        try:
            db.session.commit()
            flash("Тест успешно создан!", "success")
            return redirect(url_for('tests'))
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при сохранении слов теста: {str(e)}", "error")
            Test.query.filter_by(id=new_test.id).delete() # Rollback Test creation if words fail
            db.session.commit()
            classes_get = [str(i) for i in range(1, 12)]
            return render_template("add_tests.html", classes=classes_get, error_message=str(e))

    else: # GET request
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
            
            # Corrected logic for completed_results: count only student completions
            completed_count = db.session.query(TestResult.id).join(User, TestResult.user_id == User.id).filter(
                TestResult.test_id == test_item.id,
                TestResult.completed_at.isnot(None),
                User.teacher == 'no'  # Ensure only student results are counted
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
        # For students, we need to check if they completed the test to link to results, especially for archived.
        for test_item in tests_query:
            student_result = TestResult.query.filter_by(
                test_id=test_item.id,
                user_id=user.id,
            ).filter(TestResult.completed_at.isnot(None)).first()

            tests_data.append({
                'test': test_item,
                'students_in_class': 0, # Not relevant for student's direct view here
                'completed_count': 0, # Not relevant
                'progress': 0, # Not relevant
                'student_completed_result_id': student_result.id if student_result else None
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
                started_at=datetime.utcnow() # Explicitly set started_at
            )
            db.session.add(test_result)
            db.session.commit()

        # Process answers
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
                # For true_false, correct_answer is 'True' or 'False'
                if user_input_answer.capitalize() == word.correct_answer: # Comparison is case-insensitive for T/F but store as True/False
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
        test_result.completed_at = datetime.utcnow()
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
        print(f"DEBUG: Accessing dictation test with link: {id}")
        print(f"DEBUG: Test object: {test}")
        print(f"DEBUG: Test.test_words count: {len(test.test_words) if test.test_words else 0}")
        if test.test_words:
            for i, tw in enumerate(test.test_words):
                print(f"DEBUG: TestWord {i}: id={tw.id}, word='{tw.word}', perevod='{tw.perevod}', correct_answer='{tw.correct_answer}'")
        
        words_list = [(word.word, word.perevod, word.correct_answer, word.id) for word in test.test_words]
        active_test_result_id = session.get('active_test_result_id')
        current_test_result = None
        if active_test_result_id:
            current_test_result = TestResult.query.get(active_test_result_id)
            # Ensure the result belongs to the current test and user
            if not (current_test_result and current_test_result.test_id == test.id and current_test_result.user_id == user.id):
                current_test_result = None # Invalidate if not matching
        
        # If no active session result, try to find an incomplete one (as before)
        if not current_test_result:
            current_test_result = TestResult.query.filter_by(
                test_id=test.id,
                user_id=user.id,
                completed_at=None
            ).first()

        return render_template('test_dictation.html', 
                             test_title=test.title, # Pass test title
                             words_data=words_list, # Changed from 'words' to 'words_data' for clarity
                             test_link_id=id,     # Pass test.link as test_link_id
                             current_test_result=current_test_result, # Pass the fetched TestResult
                             time_limit_seconds=test.time_limit * 60 if test.time_limit else 0,
                             test_db_id=test.id # Pass the actual database ID of the test for submission form
                             )
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
    # TODO: Pass all words for the selected class/module to the template for "selected_specific" option
    # For now, this is handled by JS fetching words.
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
    
    if user.teacher == 'no':
        # Student access logic
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
                # If student already completed an active test, show results. Or allow retake via take_test?
                # For now, let's be consistent: if completed, show results.
                flash("Вы уже завершили этот тест. Просмотр ваших результатов.", "info")
                return redirect(url_for('test_results', test_id=test.id, result_id=student_completed_result.id))
            else:
                # If active and not completed (or no result at all), student should be able to take it.
                # The take_test route will handle if they have an in-progress one.
                return redirect(url_for('take_test', test_link=test.link))
    
    # Teacher's view (or if any other case, though students are handled above)
    # The original teacher logic for test_details remains below this block

    # Get all students in the test's class
    students_in_class = User.query.filter_by(class_number=test.classs, teacher='no').all()
    total_students_in_class = len(students_in_class)

    # Get all test results for this test
    all_results_for_test = TestResult.query.filter_by(test_id=test.id).all()

    completed_students_details = []
    in_progress_students_details = []
    not_started_student_ids = {s.id for s in students_in_class}

    for result in all_results_for_test:
        student_user = User.query.get(result.user_id)
        if not student_user: # Should not happen if DB is consistent
            continue

        # Skip results from teachers
        if student_user.teacher == 'yes':
            if result.user_id in not_started_student_ids:
                 not_started_student_ids.remove(result.user_id)
            continue

        if result.user_id in not_started_student_ids:
            not_started_student_ids.remove(result.user_id)
        
        if result.completed_at:
            completed_students_details.append({'user': student_user, 'result': result})
        else:
            # This student is in progress
            item_data_for_template = {
                'user': student_user,
                'result': result,
                'remaining_time_display': "Calculating...", # Placeholder, will be overwritten
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
            else:
                item_data_for_template['remaining_time_display'] = "Без ограничений"
                item_data_for_template['has_time_limit'] = False # Explicitly ensure it's false
            
            in_progress_students_details.append(item_data_for_template)

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
    current_user = None
    # Consolidate authentication to be cookie-based like other routes
    for cookie_name in request.cookies:
        user_obj = User.query.filter_by(nick=cookie_name).first()
        if user_obj:
            secret_key_expected = bs64.b64encode(str.encode(user_obj.nick + user_obj.password[:2])).decode("utf-8")
            if request.cookies.get(cookie_name) == secret_key_expected:
                current_user = user_obj
                break
    
    if not current_user:
        flash("Пожалуйста, войдите в систему, чтобы пройти тест.", "error")
        return redirect(url_for('login'))

    test = Test.query.filter_by(link=test_link).first_or_404()

    # Check if student belongs to the correct class for the test
    if current_user.teacher == 'no' and test.classs != current_user.class_number:
        flash("Вы не можете пройти этот тест, так как он предназначен для другого класса.", "error")
        return redirect(url_for('tests'))

    # Check if the test is active (students cannot take archived tests)
    if current_user.teacher == 'no' and not test.is_active:
        flash("Этот тест больше не активен и не может быть пройден.", "error")
        return redirect(url_for('tests'))

    # Check if student has already completed this test (or started and not finished)
    existing_result = TestResult.query.filter_by(
        test_id=test.id,
        user_id=current_user.id # Use current_user.id from cookie auth
        # completed_at=None # Keep this if we want to allow resuming, remove if only one start is allowed
    ).first()

    if request.method == 'POST': # This POST is to *start* the test
        if not existing_result or existing_result.completed_at: # Allow starting if no result or previous one completed
            # If allowing re-takes, ensure a new result is created or old one is handled.
            # For simplicity, let's assume a student starts a new attempt if prior one is completed or non-existent.
            # If there's an INCOMPLETE one, the GET request below should handle resuming it.
            
            # If there is an existing completed result, and you want to prevent retakes, check here:
            # if existing_result and existing_result.completed_at:
            #     flash("Вы уже завершили этот тест.", "info")
            #     return redirect(url_for('test_results', test_id=test.id, result_id=existing_result.id))

            test_result_to_use = TestResult.query.filter_by(
                test_id=test.id,
                user_id=current_user.id,
                completed_at=None
            ).first()

            if not test_result_to_use: # No incomplete test, create a new one
                test_result_to_use = TestResult(
                    test_id=test.id,
                    user_id=current_user.id,
                    total_questions=len(test.test_words),
                    started_at=datetime.utcnow() # Explicitly set started_at
                )
                db.session.add(test_result_to_use)
                db.session.commit()
            
            # Redirect to the actual test taking interface, e.g., test_id or a specific rendering page
            # The current logic seems to POST to /tests/<id> to submit answers.
            # This /take_test POST is more like an explicit "Start Test" action.
            # For now, let's assume starting the test means we show the first question/test interface.
            # The original code returned jsonify({'success': True}), which implies an AJAX call to start.
            # A redirect to the test interface is more straightforward for a non-AJAX flow.
            # Let's redirect to the test view which will be specific to test type.
            session['active_test_result_id'] = test_result_to_use.id # Store active test result for this session
            return jsonify({'success': True, 'redirect_url': url_for('test_id', id=test.link)}) # New: Return JSON with redirect URL
        else: # existing_result is incomplete
            session['active_test_result_id'] = existing_result.id
            return jsonify({'success': True, 'redirect_url': url_for('test_id', id=test.link)}) # New: Return JSON with redirect URL

    # GET request logic:
    # If there's an existing incomplete test result, student should resume it.
    incomplete_result = TestResult.query.filter_by(
        test_id=test.id,
        user_id=current_user.id,
        completed_at=None
    ).first()

    if incomplete_result:
        # If student has an incomplete test, take them directly to it to resume
        session['active_test_result_id'] = incomplete_result.id
        # Redirect to the test interface itself (test_id handles rendering based on type)
        return redirect(url_for('test_id', id=test.link))

    # If test is completed, show link to results or message
    completed_result = TestResult.query.filter(
        TestResult.test_id == test.id,
        TestResult.user_id == current_user.id,
        TestResult.completed_at.isnot(None)
    ).order_by(TestResult.completed_at.desc()).first()

    if completed_result:
        flash("Вы уже завершили этот тест. Посмотрите свои результаты.", "info")
        return redirect(url_for('test_results', test_id=test.id, result_id=completed_result.id))

    # Otherwise, show the test start page (if it's a GET request and no active/completed test for this user)
    return render_template('test_start.html', test=test, user=current_user)

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
        elif test.type == 'dictation':
            # For dictation, compare with TestWord.correct_answer
            if answer == word.correct_answer.lower():
                score += 1
        elif test.type == 'true_false': # Assuming true_false still compares with word.word as statement
             # For true_false, the TestWord.word is the statement, TestWord.correct_answer is 'True' or 'False'
            if answer.capitalize() == word.correct_answer: # Compare with correct_answer which should be 'True' or 'False'
                score += 1
        else: # Default fallback or other specific types if any
            # For other types (e.g. fill_word which might be like dictation)
            # if it relies on comparing user input to TestWord.correct_answer:
            if answer == word.correct_answer.lower(): 
                score += 1

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

    # Verify access to results
    can_view_results = False
    if result.user_id == user.id: # Student viewing their own results
        can_view_results = True
    elif user.teacher == 'yes' and test.created_by == user.id: # Teacher viewing results of a test they created
        can_view_results = True

    if not can_view_results:
        flash("У вас нет доступа для просмотра этих результатов.", "warning")
        return redirect(url_for('tests'))

    show_detailed_results = True
    if test.type == 'dictation' and test.is_active:
        show_detailed_results = False

    # Get detailed results
    detailed_answers = [] # Changed variable name for clarity
    if show_detailed_results: # Only fetch if we are going to show them
        for answer_obj in result.test_answers: # answer_obj is a TestAnswer instance
            test_word_instance = answer_obj.test_word # This is the TestWord instance
            
            # Determine what was presented as the 'question' based on test type
            question_presented = test_word_instance.word # Default (e.g., dictation cue, add_letter gap word)
            prompt_or_support = test_word_instance.perevod # Default (e.g., dictation audio prompt, add_letter translation)

            if test.type == 'multiple_choice_single' or test.type == 'multiple_choice_multiple':
                question_presented = test_word_instance.perevod # For MC, perevod is the question/prompt like "Choose translation for X"
                prompt_or_support = test_word_instance.word    # and word field stored the actual options or question context for options
                                                            # However, correct_answer is the definitive right choice.
            elif test.type == 'fill_word':
                question_presented = test_word_instance.word # Student sees translation (word field)
                prompt_or_support = test_word_instance.perevod # Prompt is like "Впишите оригинал"
            elif test.type == 'true_false':
                question_presented = test_word_instance.word # This is the statement
                prompt_or_support = test_word_instance.perevod # "Верно или неверно?"

            detailed_answers.append({
                'question_presented': question_presented, # What the student primarily saw as the question item
                'prompt_or_support': prompt_or_support, # Supporting info (e.g. translation for dictation, or options for MC)
                'user_answer': answer_obj.user_answer,
                'actual_correct_answer': test_word_instance.correct_answer, # The definitive correct answer
                'is_correct': answer_obj.is_correct,
                'options': test_word_instance.options # Pass options if any (for MC tests)
            })

    return render_template('test_results.html',
        test=test,
        score=result.score,
        correct_answers=result.correct_answers,
        total_questions=result.total_questions,
        time_taken=result.time_taken,
        incorrect_answers=result.total_questions - result.correct_answers,
        results_summary=detailed_answers, # Changed variable name passed to template
        show_detailed_results=show_detailed_results
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
        print("Database tables created. Running test.py...") # Optional: for logging
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
