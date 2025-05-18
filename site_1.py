from markupsafe import escape
from flask import Flask, jsonify, request, render_template, redirect, url_for, flash, make_response, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash # Added for password hashing
import time
import sqlite3
import random
import string
from datetime import datetime, timedelta
import json
import subprocess # Added to run external scripts
import re # Add this at the top with other imports



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
    password = db.Column(db.String, nullable=False) # Will store hashed password
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
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        # This case should ideally not happen if session is managed correctly
        session.pop('user_id', None)
        flash("Пользователь не найден, пожалуйста, войдите снова.", "error")
        return redirect(url_for('login'))
        
    return render_template('profile.html', nick=user.nick, fio=user.fio)


@app.route("/add_tests", methods=['POST', 'GET'])
def add_tests():
    if 'user_id' not in session:
        flash("Доступ запрещен. Пожалуйста, войдите как учитель.", "warning")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or user.teacher != 'yes':
        flash("Доступ запрещен. Только учителя могут добавлять тесты.", "warning")
        if not user:
            session.pop('user_id', None)
        return redirect(url_for('login'))
    
    if request.method == "POST":
        test_type = request.form.get('test_type')
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
        else: # No modules selected or error
            new_test_params['unit'] = "N/A" # Default if no specific module context
            new_test_params['module'] = "N/A"

        new_test = Test(**new_test_params)
        db.session.add(new_test)
        
        try:
            db.session.commit() # Commit Test object to get its ID

            if new_test.word_order == 'random':
                random.shuffle(words_data_source)
            
            final_word_count_to_use = new_test.word_count
            if final_word_count_to_use is not None and final_word_count_to_use > 0:
                words_data_source = words_data_source[:final_word_count_to_use]
            elif final_word_count_to_use == 0: # Explicitly 0 means no words
                words_data_source = []

            # If no words are sourced, and it's manual_letters, it will show "no words to configure" on the next page.
            # This might be okay, or you could flash a specific warning here and redirect differently.
            # For now, allowing it to proceed.

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
                    elif test_mode == 'manual_letters':
                        current_word_for_test_word_model = original_word_text
                        correct_answer_for_db = "" 
                        missing_letters_positions_db = None  
                            
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
                    correct_answer_for_db = original_word_text 
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
            
            db.session.commit() # Commit TestWord objects

            if new_test.type == 'add_letter' and new_test.test_mode == 'manual_letters':
                flash("Тест создан. Теперь укажите, какие буквы пропустить в словах.", "info")
                return redirect(url_for('configure_test_words', test_id=new_test.id))
            else:
                flash("Тест успешно создан!", "success")
                return redirect(url_for('tests')) # Or consider redirecting to test_details

        except Exception as e:
            db.session.rollback()
            # If new_test.id exists, it means the Test object might have been committed
            # before the exception during TestWord creation or the second commit.
            # So, we explicitly delete the Test object to avoid an orphaned Test.
            if new_test.id:
                test_to_delete = Test.query.get(new_test.id)
                if test_to_delete:
                    db.session.delete(test_to_delete)
                    db.session.commit() # Commit the deletion of the orphaned Test
            
            flash(f"Ошибка при создании теста или его слов: {str(e)}", "error")
            classes_get = [str(i) for i in range(1, 12)]
            # Pass back form data to repopulate the form
            return render_template("add_tests.html", classes=classes_get, error_message=str(e), **request.form)

    else: # GET request
        classes = [str(i) for i in range(1, 12)]
        # Pass any form data back if it was a failed POST that rendered GET
        form_data = request.form if request.form else {}
        return render_template("add_tests.html", classes=classes, **form_data)

@app.route("/tests")
def tests():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        session.pop('user_id', None)
        flash("Пользователь не найден, пожалуйста, войдите снова.", "error")
        return redirect(url_for('login'))

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
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        session.pop('user_id', None)
        flash("Пользователь не найден, пожалуйста, войдите снова.", "error")
        return redirect(url_for('login'))

    test = Test.query.filter_by(link=id).first()
    if not test:
        return "Test not found", 404

    is_teacher_preview_mode = False # Flag to indicate teacher preview

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
        if test.classs != user.class_number:
            flash("Доступ запрещен: тест предназначен для другого класса.", "error")
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

        words_list = []
        for word in test.test_words:
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
            words_list.append({
                'id': word.id,
                'word': word.word, 
                'perevod': word.perevod,
                'num_inputs': len(word.correct_answer) if word.correct_answer else 0
            })
        return render_template('test_add_letter.html', 
                             words=words_list, 
                             test_id=id, # link
                             test_result=test_result, # Will be None for teacher preview
                             time_limit=test.time_limit,
                             remaining_time_seconds=remaining_time_seconds,
                             test_title=test.title, 
                             test_db_id=test.id, # numerical ID
                             is_teacher_preview=is_teacher_preview_mode) # Pass the preview flag
    elif test.type == 'dictation':
        # Debug prints can be removed
        # print(f"DEBUG: Accessing dictation test with link: {id}")
        # print(f"DEBUG: Test object: {test}")
        # print(f"DEBUG: Test.test_words count: {len(test.test_words) if test.test_words else 0}")
        # if test.test_words:
        #     for i, tw in enumerate(test.test_words):
        #         print(f"DEBUG: TestWord {i}: id={tw.id}, word='{tw.word}', perevod='{tw.perevod}', correct_answer='{tw.correct_answer}'")
        
        words_list = [(word.word, word.perevod, word.correct_answer, word.id) for word in test.test_words]
        
        current_test_result_for_template = test_result # Use the one determined by student/teacher logic
        if is_teacher_preview_mode:
            current_test_result_for_template = None # Ensure no result object for teacher preview

        return render_template('test_dictation.html', 
                             test_title=test.title,
                             words_data=words_list,
                             test_link_id=id,
                             current_test_result=current_test_result_for_template, # Pass the correct result object
                             time_limit_seconds=test.time_limit * 60 if test.time_limit else 0,
                             remaining_time_seconds=remaining_time_seconds,
                             test_db_id=test.id,
                             is_teacher_preview=is_teacher_preview_mode) # Pass the preview flag
    elif test.type == 'true_false': # Assuming this was a typo for true_false
        words_list = [(word.word, word.perevod, word.id) for word in test.test_words] # Added word.id
        return render_template('test_true_false.html', # Corrected template name
                             words=words_list, 
                             test_id=id, # link
                             test_result=test_result, # Will be None for teacher preview
                             time_limit=test.time_limit,
                             remaining_time_seconds=remaining_time_seconds,
                             test_title=test.title,
                             test_db_id=test.id,
                             is_teacher_preview=is_teacher_preview_mode)
    elif test.type == 'multiple_choice': # Assuming this is multiple_choice_single from context
        words_list = []
        for word in test.test_words:
            options = word.options.split('|') if word.options else []
            words_list.append({
                'id': word.id,
                'word': word.word, # This is the question (e.g., translation)
                'perevod': word.perevod, # This is the prompt (e.g., "Choose the correct word")
                'options': options
            })
        return render_template('test_multiple_choice.html', 
                             words=words_list, 
                             test_id=id, # link
                             test_result=test_result, # Will be None for teacher preview
                             time_limit=test.time_limit,
                             remaining_time_seconds=remaining_time_seconds,
                             test_title=test.title,
                             test_db_id=test.id,
                             is_teacher_preview=is_teacher_preview_mode)
    elif test.type == 'fill_word':
        words_list = []
        for word in test.test_words:
            words_list.append({
                'id': word.id,
                'word': word.word, # This is the question (e.g., translation)
                'perevod': word.perevod # This is the prompt (e.g., "Fill in the original word")
            })
        return render_template('test_fill_word.html', # Assuming a template test_fill_word.html exists
                             words=words_list,
                             test_id=id, # link
                             test_result=test_result, # Will be None for teacher preview
                             time_limit=test.time_limit,
                             remaining_time_seconds=remaining_time_seconds,
                             test_title=test.title,
                             test_db_id=test.id,
                             is_teacher_preview=is_teacher_preview_mode)
    elif test.type == 'multiple_choice_multiple':
        words_list = []
        for word in test.test_words:
            options = word.options.split('|') if word.options else []
            words_list.append({
                'id': word.id,
                'word': word.word,       # Question (e.g., translation/definition)
                'perevod': word.perevod, # Prompt (e.g., "Select all correct options")
                'options': options
            })
        return render_template('test_multiple_choice_multiple.html', # Assuming this template exists
                             words=words_list,
                             test_id=id, # link
                             test_result=test_result, # Will be None for teacher preview
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
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.pop('user_id', None)
        flash("Пользователь не найден, пожалуйста, войдите снова.", "error")
        return redirect(url_for('login'))
        
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
        password_form = request.form['password']

        if username == 'teacher':
            teacher_user = User.query.filter_by(nick='teacher').first()
            if teacher_user and check_password_hash(teacher_user.password, password_form):
                session['user_id'] = teacher_user.id
                session.permanent = True  # Make session last for a while
                app.permanent_session_lifetime = timedelta(days=15)
                return redirect(url_for('hello'))
            elif not teacher_user and password_form == 'teacher': # First time teacher login or fallback
                hashed_password = generate_password_hash('teacher')
                teacher = User(
                    fio='Teacher',
                    nick='teacher',
                    password=hashed_password,
                    teacher='yes'
                )
                db.session.add(teacher)
                db.session.commit()
                session['user_id'] = teacher.id
                session.permanent = True
                app.permanent_session_lifetime = timedelta(days=15)
                return redirect(url_for('hello'))
            else:
                error = 'Invalid teacher credentials'
        else:
            user = User.query.filter_by(nick=username).first()
            if user and check_password_hash(user.password, password_form):
                session['user_id'] = user.id
                session.permanent = True
                app.permanent_session_lifetime = timedelta(days=15)
                return redirect(url_for('hello'))
            else:
                error = 'Invalid username/password'

    return render_template('login.html', error=error)

@app.route("/logout")
def logout():
    session.pop('user_id', None)
    flash("Вы успешно вышли из системы.", "info")
    return redirect(url_for('login'))

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

        existing_user = User.query.filter_by(nick=username).first()
        if existing_user:
            error = "Выбранный вами Username уже занят"
            return render_template('registration.html', error=error, fio=fio, username=username, selected_class=class_number, classes=[str(i) for i in range(1, 12)])

        fio_in_mass = fio.split(' ')
        if len(fio_in_mass) != 3: # Assuming FIO should be 3 words
            error = "ФИО должно состоять из 3 слов"
            return render_template('registration.html', error=error, fio=fio, username=username, selected_class=class_number, classes=[str(i) for i in range(1, 12)])

        hashed_password = generate_password_hash(password)
        
        # Removed max_id logic as primary key should auto-increment by default
        new_user = User(
            fio=fio,
            nick=username,
            password=hashed_password,
            teacher='no',
            class_number=class_number
        )
        db.session.add(new_user)
        db.session.commit()
        
        # Log the user in immediately after registration
        session['user_id'] = new_user.id
        session.permanent = True
        app.permanent_session_lifetime = timedelta(days=15)
        flash("Регистрация прошла успешно! Вы вошли в систему.", "success")
        return redirect(url_for('hello'))

    classes = [str(i) for i in range(1, 12)]  # Classes 1-11
    return render_template('registration.html', error=error, classes=classes)

@app.route("/hello")
def hello():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        session.pop('user_id', None) # Clean up invalid session
        flash("Пользователь не найден, пожалуйста, войдите снова.", "error")
        return redirect(url_for('login'))

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
    if 'user_id' not in session:
        flash("Доступ запрещен. Пожалуйста, войдите как учитель.", "warning")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or user.teacher != 'yes':
        flash("Доступ запрещен. Только учителя могут создавать тесты.", "warning")
        if not user: # If user is None (e.g. ID in session is invalid), pop session and redirect
            session.pop('user_id', None)
        return redirect(url_for('login'))
    
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

        db.session.commit() # Commit TestWord entries. Test object (new_test) was committed earlier.

        # Use new_test.type and new_test.test_mode for the redirect condition
        if new_test.type == 'add_letter' and new_test.test_mode == 'manual_letters':
            flash("Тест создан. Теперь укажите, какие буквы пропустить в словах.", "info")
            return redirect(url_for('configure_test_words', test_id=new_test.id))
        else:
            flash("Тест успешно создан!", "success")
            return redirect(url_for('test_details', test_id=new_test.id))

    # GET request:
    user = User.query.get(session['user_id']) # Ensure user is fetched for GET request as well
    # Fetch available modules to populate the form (example, adjust as per actual logic)
    available_modules = {} # Replace with actual module fetching logic if needed for the GET request
    classes_get = [str(i) for i in range(1, 12)]
    
    # Pass any other necessary context for the template
    return render_template("create_test.html", user=user, classes=classes_get, available_modules=available_modules)

@app.route('/configure_test_words/<int:test_id>', methods=['GET', 'POST'])
def configure_test_words(test_id):
    if 'user_id' not in session:
        flash("Доступ запрещен. Пожалуйста, войдите.", "warning")
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
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

@app.route("/test/<int:test_id>")
def test_details(test_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        session.pop('user_id', None)
        flash("Пользователь не найден, пожалуйста, войдите снова.", "error")
        return redirect(url_for('login'))

    test = Test.query.get_or_404(test_id)
    
    if user.teacher == 'yes':
        # Teacher's view: Gather student progress and render details page
        students_in_class = User.query.filter_by(class_number=test.classs, teacher='no').all()
        total_students_in_class = len(students_in_class)
        all_results_for_test = TestResult.query.filter_by(test_id=test.id).all()

        completed_students_details = []
        in_progress_students_details = []
        not_started_student_ids = {s.id for s in students_in_class}

        for result in all_results_for_test:
            student_user = User.query.get(result.user_id)
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

        not_started_students = [User.query.get(uid) for uid in not_started_student_ids]
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
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
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
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
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
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
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
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
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
        return redirect(url_for('login'))

    current_user = User.query.get(session['user_id'])
    if not current_user:
        session.pop('user_id', None)
        flash("Пользователь не найден, пожалуйста, войдите снова.", "error")
        return redirect(url_for('login'))
    
    test = Test.query.filter_by(link=test_link).first_or_404()

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
            return jsonify({'success': True, 'redirect_url': url_for('test_id', id=test.link)})

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
            return jsonify({'success': True, 'redirect_url': url_for('test_id', id=test.link)})
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
            return jsonify({'success': True, 'redirect_url': url_for('test_id', id=test.link)})

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
        # For form submissions, redirect is more appropriate than JSON error
        flash("Аутентификация не пройдена. Пожалуйста, войдите снова.", "error")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        flash("Пользователь не найден. Пожалуйста, войдите снова.", "error")
        return redirect(url_for('login'))

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
        
        # TODO: Adapt logic for other test types if they also switch from JSON to form submission.
        # The following is placeholder logic and assumes other types might send answers via request.form[{test_word.id}] or similar
        # This section needs careful review if other test types are changed.
        elif test.type == 'multiple_choice_single': # Example
            user_submitted_answer_string = request.form.get(f'answer_{test_word.id}', '').strip()
            is_correct = user_submitted_answer_string.lower() == test_word.correct_answer.lower()
        elif test.type == 'dictation': # Example
            # OLD: user_submitted_answer_string = request.form.get(f'answer_{test_word.id}', '').strip()
            # NEW: Reconstruct the answer string from individual character inputs
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
    active_test_result.completed_at = datetime.utcnow()
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
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        session.pop('user_id', None)
        flash("Пользователь не найден, пожалуйста, войдите снова.", "error")
        return redirect(url_for('login'))

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
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.pop('user_id', None)
        flash("Пользователь не найден, пожалуйста, войдите снова.", "error")
        return redirect(url_for('login'))
        
    return render_template('games.html', is_teacher=user.teacher == 'yes')

@app.route('/test_details_data/<int:test_id>')
def test_details_data(test_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    user = User.query.get(session['user_id'])
    if not user or user.teacher != 'yes': # Only teachers should access this live data endpoint
        return jsonify({'error': 'Forbidden for non-teachers'}), 403

    test = Test.query.get_or_404(test_id)
    if test.created_by != user.id:
        return jsonify({'error': 'Forbidden, not test creator'}), 403

    students_in_class = User.query.filter_by(class_number=test.classs, teacher='no').all()
    total_students_in_class = len(students_in_class)
    all_results_for_test = TestResult.query.filter_by(test_id=test.id).all()

    completed_students_details_json = []
    in_progress_students_details_json = []
    not_started_student_ids = {s.id for s in students_in_class}

    for result in all_results_for_test:
        student_user = User.query.get(result.user_id)
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
                'total_questions': result.total_questions
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
        s_user = User.query.get(uid)
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
