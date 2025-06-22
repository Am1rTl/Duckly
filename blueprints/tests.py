from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash, session, abort
from models import db, User, Test, TestWord, TestResult, TestAnswer, TextTestAnswer, TextContent, TextQuestion
from blueprints.utils import get_current_user, require_login, require_teacher, generate_options_with_fallback, format_time_taken, auto_clear_previous_test_results
from datetime import datetime, timedelta
import json
import random
import string
import re

tests_bp = Blueprint('tests', __name__)

# Root of tests blueprint: redirect to welcome page
@tests_bp.route('/')
@require_login
def tests_root():
    # Show list page for teachers, hello for students
    user = get_current_user()
    if user and user.teacher == 'yes':
        # Keep query parameters so ?show_archived=true works
        target_url = url_for('tests.tests', **request.args)
        return redirect(target_url)
    return redirect(url_for('tests.hello'))

@tests_bp.route('/hello')
@require_login
def hello():
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))
    username = user.fio or user.nick or ''
    letters = ''.join([p[0].upper() for p in username.split() if p])[:2] or (user.nick[:2].upper() if user.nick else '')
    return render_template('hello.html', user=user, username=username, letters=letters)

@tests_bp.route('/add', methods=['GET', 'POST'])
@require_login
@require_teacher
def add_tests():
    user = get_current_user()
    
    if request.method == 'POST':
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
            'link': ''.join(random.choices(string.ascii_letters + string.digits, k=10)),
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
                    flash(f"Invalid module identifier: {module_identifier}", "warning")

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
                flash("Text-based tests require text content of at least 50 characters.", "error")
                classes_get = [str(i) for i in range(1, 12)]
                return render_template("add_tests.html", classes=classes_get, **request.form)
            new_test = Test(**new_test_params)
            db.session.add(new_test)
            db.session.commit()
            flash("Test created. Now add questions based on the uploaded text.", "info")
            return redirect(url_for('tests.create_text_based_test', test_id=new_test.id))

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
                flash("Test created. Now specify which letters to omit in the words.", "info")
                return redirect(url_for('tests.configure_test_words', test_id=new_test.id))
            else:
                flash("Test successfully created!", "success")
                return redirect(url_for('tests.tests'))

        except Exception as e:
            db.session.rollback()
            if new_test.id:
                test_to_delete = db.session.get(Test, new_test.id)
                if test_to_delete:
                    db.session.delete(test_to_delete)
                    db.session.commit()
            flash(f"Error creating test or its words: {str(e)}", "error")
            classes_get = [str(i) for i in range(1, 12)]
            return render_template("add_tests.html", classes=classes_get, error_message=str(e), **request.form)

    else:
        classes = [str(i) for i in range(1, 12)]
        form_data = request.form if request.form else {}
        return render_template("add_tests.html", classes=classes, **form_data)

@tests_bp.route('/list')
@require_login
def tests():
    user = get_current_user()
    show_archived = request.args.get('show_archived', 'false') == 'true'
    
    tests_data = []
    if user.teacher == 'yes':
        tests_query = Test.query.filter_by(created_by=user.id, is_active=not show_archived).order_by(Test.created_at.desc()).all()
        for test_item in tests_query:
            students_in_class = User.query.filter_by(class_number=test_item.classs, teacher='no').count()
            
            completed_count = db.session.query(TestResult.id).join(User, TestResult.user_id == User.id).filter(
                TestResult.test_id == test_item.id,
                TestResult.completed_at.isnot(None),
                User.teacher == 'no',
                TestResult.started_at >= test_item.created_at
            ).count()

            progress = 0
            if students_in_class > 0:
                progress = round((completed_count / students_in_class) * 100)
            
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
        tests_query = Test.query.filter_by(classs=user.class_number, is_active=not show_archived).order_by(Test.created_at.desc()).all()
        for test_item in tests_query:
            student_result = TestResult.query.filter_by(
                test_id=test_item.id,
                user_id=user.id,
            ).filter(TestResult.completed_at.isnot(None)).first()

            text_content = None
            if test_item.type == 'text_based' and test_item.text_content_id:
                text_content = db.session.get(TextContent, test_item.text_content_id)

            tests_data.append({
                'test': test_item,
                'students_in_class': 0,
                'completed_count': 0,
                'progress': 0,
                'student_completed_result_id': student_result.id if student_result else None,
                'text_content': text_content
            })

    return render_template('tests.html', tests_data=tests_data, show_archived=show_archived, is_teacher=user.teacher == 'yes')

@tests_bp.route('/progress')
@require_login
@require_teacher
def api_tests_progress():
    user = get_current_user()
    tests_query = Test.query.filter_by(created_by=user.id, is_active=True).order_by(Test.created_at.desc()).all()
    
    progress_data = []
    for test_item in tests_query:
        students_in_class = User.query.filter_by(class_number=test_item.classs, teacher='no').count()
        
        completed_count = db.session.query(TestResult.id).join(User, TestResult.user_id == User.id).filter(
            TestResult.test_id == test_item.id,
            TestResult.completed_at.isnot(None),
            User.teacher == 'no',
            TestResult.started_at >= test_item.created_at
        ).count()

        progress_data.append({
            'id': test_item.id,
            'title': test_item.title,
            'students_in_class': students_in_class,
            'completed_count': completed_count
        })
        
    return jsonify(progress_data)

@tests_bp.route('/<test_link>', methods=['GET', 'POST'])
@require_login
def test_id(test_link):
    user = get_current_user()
    test = Test.query.filter_by(link=test_link).first()
    if not test:
        abort(404)

    is_teacher_preview_mode = user.teacher == 'yes' and (session.get('is_teacher_preview', False) or session.get('test_link') == test_link)
    
    test_result = None
    if not is_teacher_preview_mode:
        if 'active_test_result_id' in session:
            test_result_id = session['active_test_result_id']
            test_result = db.session.get(TestResult, test_result_id)
        
        if not test_result and 'active_test_result_id' in request.cookies:
            try:
                test_result_id = int(request.cookies.get('active_test_result_id'))
                test_result = db.session.get(TestResult, test_result_id)
                if test_result:
                    session['active_test_result_id'] = test_result_id
                    session['test_link'] = test_link
                    session.modified = True
            except (ValueError, TypeError):
                pass
    
        if user.teacher == 'no' and not test_result:
            incomplete_result = TestResult.query.filter_by(
                test_id=test.id,
                user_id=user.id,
                completed_at=None
            ).first()
            
            if incomplete_result:
                test_result = incomplete_result
                session['active_test_result_id'] = incomplete_result.id
                session['test_link'] = test_link
                session.modified = True
    
    if request.method == 'POST':
        if is_teacher_preview_mode:
            flash("Teachers cannot submit tests in preview mode.", "warning")
            return redirect(url_for('tests.tests'))
        
        if not test_result:
            test_result = TestResult(
                test_id=test.id,
                user_id=user.id,
                total_questions=TestWord.query.filter_by(test_id=test.id).count(),
                started_at=datetime.utcnow()
            )
            db.session.add(test_result)
            db.session.commit()
            session['active_test_result_id'] = test_result.id
            session['test_link'] = test_link
            session.modified = True
        
        answers_json_for_db = {}
        detailed_results_for_db = []
        current_score_count = 0
        total_questions = test_result.total_questions
        
        test_words = TestWord.query.filter_by(test_id=test.id).all()
        if test.word_order == 'random':
            seed_value = hash(f"{user.id}_{test.id}") % (2**32)
            random.seed(seed_value)
            test_words = random.sample(test_words, len(test_words))
            random.seed()
        
        for test_word in test_words:
            if test.type == 'dictation':
                current_word_chars_map = {}
                for key in request.form:
                    if key.startswith(f'char_{test_word.id}_'):
                        try:
                            char_idx_str = key[len(f'char_{test_word.id}_'):]
                            char_idx = int(char_idx_str)
                            char_value = request.form[key]
                            if len(char_value) > 1:
                                char_value = char_value[0]
                            current_word_chars_map[char_idx] = char_value
                        except ValueError:
                            print(f"Warning: Could not parse char index from key {key} for dictation word {test_word.id}")
                
                answer_chars = []
                if current_word_chars_map:
                    max_idx_found = max(current_word_chars_map.keys()) if current_word_chars_map else -1
                    for i in range(max_idx_found + 1):
                        answer_chars.append(current_word_chars_map.get(i, ""))
                
                user_submitted_answer_string = "".join(answer_chars)
                normalized_user_answer = re.sub(r'[\s\.,!?-]', '', user_submitted_answer_string).lower()
                normalized_correct_answer = re.sub(r'[\s\.,!?-]', '', test_word.correct_answer).lower()
                is_correct = normalized_user_answer == normalized_correct_answer
            elif test.type == 'true_false':
                user_submitted_answer_string = request.form.get(f'answer_{test_word.id}', '').strip()
                is_correct = user_submitted_answer_string.capitalize() == test_word.correct_answer
            else:
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

        test_result.score = int((current_score_count / total_questions) * 100) if total_questions > 0 else 0
        test_result.correct_answers = current_score_count
        test_result.total_questions = total_questions
        completion_time = datetime.utcnow()
        test_result.completed_at = completion_time
        
        if test_result.started_at:
            time_diff = completion_time - test_result.started_at
            test_result.time_taken = max(0, int(time_diff.total_seconds() / 60))
        else:
            test_result.time_taken = 0
        
        test_result.answers = json.dumps(answers_json_for_db)
        
        for ans_data in detailed_results_for_db:
            test_answer_entry = TestAnswer(
                test_result_id=test_result.id,
                test_word_id=ans_data['test_word_id'],
                user_answer=ans_data['user_answer'],
                is_correct=ans_data['is_correct']
            )
            db.session.add(test_answer_entry)
        
        try:
            db.session.commit()
            flash("Test successfully completed!", "success")
            return redirect(url_for('tests.test_results', test_id=test.id, result_id=test_result.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error saving test results: {str(e)}", "error")
            return redirect(url_for('tests.test_id', test_link=test.link))
    
    test_words = TestWord.query.filter_by(test_id=test.id)
    if test.word_order == 'random':
        seed_value = hash(f"{user.id}_{test.id}") % (2**32)
        random.seed(seed_value)
        test_words = random.sample(list(test_words), test_words.count())
        random.seed()
    else:
        test_words = test_words.order_by(TestWord.word_order).all()

    # Prepare words data for frontend
    words_json = []
    for tw in test_words:
        words_json.append({
            'id': tw.id,
            'word': tw.word,
            # include additional fields depending on test type
            'missing_letter_index': getattr(tw, 'missing_letter_index', None),
            'perevod': tw.perevod,
            'correct_answer': getattr(tw, 'correct_answer', None),
            'options': json.loads(tw.options) if tw.options else None,
            'missing_letters': getattr(tw, 'missing_letters', None)
        })
    
    return render_template('take_test.html',
                           test=test,
                           words_json=words_json,
                           test_result=test_result,
                           is_teacher_preview=is_teacher_preview_mode)

@tests_bp.route('/results/<int:test_id>/<int:result_id>')
@require_login
def test_results(test_id, result_id):
    user = get_current_user()
    test = db.session.get(Test, test_id)
    if not test:
        flash('Test not found', 'error')
        return redirect(url_for('tests.tests'))
    
    result = db.session.get(TestResult, result_id)
    if not result:
        flash('Test result not found', 'error')
        return redirect(url_for('tests.tests'))
    
    can_view_results = result.user_id == user.id or (user.teacher == 'yes' and test.created_by == user.id)
    if not can_view_results:
        flash("You do not have access to view these results.", "warning")
        return redirect(url_for('tests.tests'))

    show_detailed_results = user.teacher == 'yes' and test.created_by == user.id or (result.user_id == user.id and not test.is_active)
    
    detailed_answers = []
    if show_detailed_results:
        for answer_obj in result.test_answers:
            test_word_instance = answer_obj.test_word
            detailed_answers_item = {
                'user_answer': answer_obj.user_answer,
                'actual_correct_answer': test_word_instance.correct_answer,
                'is_correct': answer_obj.is_correct,
                'options': test_word_instance.options,
                'student_reconstructed_parts': None,
                'correct_reconstructed_parts': None
            }

            if test.type == 'add_letter':
                detailed_answers_item['question_presented'] = test_word_instance.word
                detailed_answers_item['prompt_or_support'] = test_word_instance.perevod

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
                                part_info['is_correct_char'] = student_letters[s_idx].lower() == correct_char_for_gap.lower()
                            except StopIteration:
                                part_info['is_correct_char'] = False
                            s_idx += 1
                        else:
                            part_info['char'] = '_'
                            part_info['is_student_input'] = True
                            part_info['is_correct_char'] = False
                    student_parts.append(part_info)
                detailed_answers_item['student_reconstructed_parts'] = student_parts

                correct_parts = []
                correct_letters = list(test_word_instance.correct_answer)
                c_idx = 0
                for char_template in gapped_template:
                    part_info = {'char': char_template, 'is_student_input': False}
                    if char_template == '_':
                        if c_idx < len(correct_letters):
                            part_info['char'] = correct_letters[c_idx]
                            part_info['is_student_input'] = True
                            c_idx += 1
                        else:
                            part_info['char'] = '_'
                    correct_parts.append(part_info)
                detailed_answers_item['correct_reconstructed_parts'] = correct_parts
            
            elif test.type in ['multiple_choice_single', 'multiple_choice_multiple']:
                detailed_answers_item['question_presented'] = test_word_instance.perevod
                detailed_answers_item['prompt_or_support'] = test_word_instance.word
            elif test.type == 'fill_word':
                detailed_answers_item['question_presented'] = test_word_instance.word
                detailed_answers_item['prompt_or_support'] = test_word_instance.perevod
            elif test.type == 'true_false':
                detailed_answers_item['question_presented'] = test_word_instance.word
                detailed_answers_item['prompt_or_support'] = test_word_instance.perevod
            else:
                detailed_answers_item['question_presented'] = test_word_instance.word
                detailed_answers_item['prompt_or_support'] = test_word_instance.perevod

            detailed_answers.append(detailed_answers_item)

    text_test_results = []
    if test.type == 'text_based' and show_detailed_results:
        questions = []
        if test.text_based_questions:
            try:
                questions = json.loads(test.text_based_questions)
            except json.JSONDecodeError:
                questions = []
        
        user_answers = {}
        if result.answers:
            try:
                user_answers = json.loads(result.answers)
            except json.JSONDecodeError:
                user_answers = {}
        
        for i, question in enumerate(questions):
            question_key = f'question_{i}'
            user_answer = user_answers.get(question_key, '')
            
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

    time_taken_display = format_time_taken(result.time_taken)
    
    return render_template('test_results.html',
                           test=test,
                           score=result.score,
                           correct_answers=result.correct_answers,
                           total_questions=result.total_questions,
                           time_taken=time_taken_display,
                           time_taken_raw=result.time_taken,
                           incorrect_answers=result.total_questions - result.correct_answers,
                           results_summary=detailed_answers,
                           show_detailed_results=show_detailed_results,
                           text_test_results=text_test_results,
                           is_teacher=user.teacher == 'yes')

@tests_bp.route('/create_text_based/<int:test_id>', methods=['GET', 'POST'])
@require_login
@require_teacher
def create_text_based_test(test_id):
    test = db.session.get(Test, test_id)
    if not test:
        flash('Test not found', 'error')
        return redirect(url_for('tests.tests'))
    
    current_user = get_current_user()
    if test.created_by != current_user.id:
        flash('You do not have permission to edit this test', 'error')
        return redirect(url_for('tests.tests'))
    
    if request.method == 'POST':
        questions_data = request.form.get('questions_data')
        if questions_data:
            try:
                questions = json.loads(questions_data)
                test.text_based_questions = json.dumps(questions, ensure_ascii=False)
                db.session.commit()
                flash('Questions successfully saved!', 'success')
                return redirect(url_for('tests.test_details', test_id=test.id))
            except json.JSONDecodeError:
                flash('Error saving questions', 'error')
        else:
            test.text_based_questions = json.dumps([], ensure_ascii=False)
            db.session.commit()
            flash('Questions cleared', 'info')
            return redirect(url_for('tests.test_details', test_id=test.id))
    
    existing_questions = []
    if test.text_based_questions:
        try:
            existing_questions = json.loads(test.text_based_questions)
        except json.JSONDecodeError:
            existing_questions = []
    
    questions_for_js = json.dumps(existing_questions, ensure_ascii=False)
    
    return render_template('configure_text_quiz.html', 
                          test=test, 
                          questions_for_js=questions_for_js)

@tests_bp.route('/take_text/<test_link>')
@require_login
def take_text_test(test_link):
    test = db.session.execute(
        db.select(Test).where(Test.link == test_link)
    ).scalar_one_or_none()
    
    if not test:
        flash('Test not found', 'error')
        return redirect(url_for('tests.hello'))
    
    if not test.is_active:
        flash('Test is not active', 'error')
        return redirect(url_for('tests.hello'))
    
    questions = []
    if test.text_content_id:
        text_questions = db.session.execute(
            db.select(TextQuestion).where(
                TextQuestion.text_content_id == test.text_content_id
            ).order_by(TextQuestion.order_number)
        ).scalars().all()
        
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
        try:
            questions = json.loads(test.text_based_questions)
        except json.JSONDecodeError:
            questions = []
    
    if not questions:
        flash('No questions in the test', 'error')
        return redirect(url_for('tests.hello'))
    
    current_user = get_current_user()
    
    existing_result = db.session.execute(
        db.select(TestResult).where(
            TestResult.test_id == test.id,
            TestResult.user_id == current_user.id,
            TestResult.completed_at.is_(None)
        )
    ).scalar_one_or_none()
    
    if existing_result:
        test_result = existing_result
    else:
        test_result = TestResult(
            test_id=test.id,
            user_id=current_user.id,
            total_questions=len(questions),
            started_at=datetime.utcnow()
        )
        db.session.add(test_result)
        db.session.commit()
    
    text_content = None
    if test.text_content_id:
        text_content = db.session.get(TextContent, test.text_content_id)
    
    return render_template('take_text_test.html', 
                          test=test, 
                          questions=questions,
                          test_result=test_result,
                          text_content=text_content)

# Generic take_test route for universal links used in templates
@tests_bp.route('/take_test/<test_link>')
@require_login
def take_test(test_link):
    """Redirects to the correct take route based on test type so that
    templates can just use `url_for('take_test', ...)`."""
    test = Test.query.filter_by(link=test_link).first_or_404()
    if test.type == 'text_based':
        return redirect(url_for('tests.take_text_test', test_link=test_link))
    else:
        # For all other test types use the main test-taking view
        return redirect(url_for('tests.test_id', test_link=test_link))

# ---------------------- Test management actions ----------------------
@tests_bp.route('/archive/<int:test_id>', methods=['POST'])
@require_login
@require_teacher
def archive_test(test_id):
    test = db.session.get(Test, test_id)
    if not test:
        flash('Test not found', 'error')
        return redirect(url_for('tests.tests'))
    current_user = get_current_user()
    if test.created_by != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('tests.tests'))
    test.is_active = False
    db.session.commit()
    flash('Test archived', 'info')
    return redirect(url_for('tests.test_details_by_link', test_link=test.link))

@tests_bp.route('/unarchive/<int:test_id>', methods=['POST'])
@require_login
@require_teacher
def unarchive_test(test_id):
    test = db.session.get(Test, test_id)
    if not test:
        flash('Test not found', 'error')
        return redirect(url_for('tests.tests'))
    current_user = get_current_user()
    if test.created_by != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('tests.tests'))
    test.is_active = True
    db.session.commit()
    flash('Test unarchived', 'info')
    return redirect(url_for('tests.test_details_by_link', test_link=test.link))

@tests_bp.route('/clear_results/<int:test_id>', methods=['POST'])
@require_login
@require_teacher
def clear_test_results(test_id):
    test = db.session.get(Test, test_id)
    if not test:
        flash('Test not found', 'error')
        return redirect(url_for('tests.tests'))
    current_user = get_current_user()
    if test.created_by != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('tests.tests'))
    # Delete related results & answers
    results = TestResult.query.filter_by(test_id=test.id).all()
    for res in results:
        TestAnswer.query.filter_by(test_result_id=res.id).delete()
        TextTestAnswer.query.filter_by(test_result_id=res.id).delete()
    TestResult.query.filter_by(test_id=test.id).delete()
    db.session.commit()
    flash('All results cleared', 'info')
    return redirect(url_for('tests.test_details_by_link', test_link=test.link))

@tests_bp.route('/delete_completely/<int:test_id>', methods=['POST'])
@require_login
@require_teacher
def delete_test_completely(test_id):
    test = db.session.get(Test, test_id)
    if not test:
        flash('Test not found', 'error')
        return redirect(url_for('tests.tests'))
    current_user = get_current_user()
    if test.created_by != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('tests.tests'))
    # Cascade delete results & answers etc.
    results = TestResult.query.filter_by(test_id=test.id).all()
    for res in results:
        TestAnswer.query.filter_by(test_result_id=res.id).delete()
        TextTestAnswer.query.filter_by(test_result_id=res.id).delete()
    TestResult.query.filter_by(test_id=test.id).delete()
    TestWord.query.filter_by(test_id=test.id).delete()
    db.session.delete(test)
    db.session.commit()
    flash('Test deleted permanently', 'info')
    return redirect(url_for('tests.tests'))

@tests_bp.route('/configure_true_false/<int:test_id>', methods=['GET', 'POST'])
@require_login
@require_teacher
def configure_true_false_test(test_id):
    # Placeholder – real config UI not yet implemented
    flash('Configuration page for true/false tests is under construction.', 'info')
    return redirect(url_for('tests.test_details_by_link', test_link=db.session.get(Test, test_id).link))

@tests_bp.route('/submit_text/<int:test_result_id>', methods=['POST'])
@require_login
def submit_text_test(test_result_id):
    test_result = db.session.get(TestResult, test_result_id)
    if not test_result:
        return jsonify({'error': 'Test result not found'}), 404
    
    current_user = get_current_user()
    if test_result.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    if test_result.completed_at:
        return jsonify({'error': 'Test already completed'}), 400
    
    test = db.session.get(Test, test_result.test_id)
    
    questions = []
    if test.text_content_id:
        text_questions = db.session.execute(
            db.select(TextQuestion).where(
                TextQuestion.text_content_id == test.text_content_id
            ).order_by(TextQuestion.order_number)
        ).scalars().all()
        questions = text_questions
    elif test.text_based_questions:
        try:
            old_questions = json.loads(test.text_based_questions)
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
    
    correct_count = 0
    total_points = 0
    earned_points = 0
    
    for i, question in enumerate(questions):
        question_key = f'question_{i}'
        user_answer = request.form.get(question_key, '').strip()
        
        is_correct = False
        points_for_question = getattr(question, 'points', 1)
        total_points += points_for_question
        
        if question.question_type == 'multiple_choice':
            is_correct = user_answer == question.correct_answer
        elif question.question_type == 'multiple_select':
            try:
                user_answers = json.loads(user_answer) if user_answer else []
                correct_answers = json.loads(question.correct_answer) if question.correct_answer else []
                is_correct = sorted(user_answers) == sorted(correct_answers)
            except json.JSONDecodeError:
                is_correct = False
        elif question.question_type == 'true_false':
            is_correct = user_answer == question.correct_answer
        elif question.question_type == 'open_answer':
            is_correct = user_answer.lower().strip() == question.correct_answer.lower().strip()
        
        if is_correct:
            correct_count += 1
            earned_points += points_for_question
        
        if hasattr(question, 'id') and isinstance(question.id, int):
            text_answer = TextTestAnswer(
                test_result_id=test_result.id,
                text_question_id=question.id,
                user_answer=user_answer,
                is_correct=is_correct,
                points_earned=points_for_question if is_correct else 0
            )
            db.session.add(text_answer)
    
    test_result.correct_answers = correct_count
    test_result.score = int((earned_points / total_points) * 100) if total_points > 0 else 0
    test_result.completed_at = datetime.utcnow()
    
    if test_result.started_at:
        time_diff = datetime.utcnow() - test_result.started_at
        test_result.time_taken = max(0, int(time_diff.total_seconds() / 60))
    else:
        test_result.time_taken = 0
    
    db.session.commit()
    
    return redirect(url_for('tests.view_text_test_result', test_result_id=test_result.id))

@tests_bp.route('/view_text_result/<int:test_result_id>')
@require_login
def view_text_test_result(test_result_id):
    test_result = db.session.get(TestResult, test_result_id)
    if not test_result:
        flash('Test result not found', 'error')
        return redirect(url_for('tests.hello'))
    
    current_user = get_current_user()
    
    if test_result.user_id != current_user.id and current_user.teacher != 'yes':
        flash('Access denied', 'error')
        return redirect(url_for('tests.hello'))
    
    test = db.session.get(Test, test_result.test_id)
    
    text_content = None
    if test.text_content_id:
        text_content = db.session.get(TextContent, test.text_content_id)
    
    detailed_results = []
    
    if test.text_content_id:
        text_questions = db.session.execute(
            db.select(TextQuestion).where(
                TextQuestion.text_content_id == test.text_content_id
            ).order_by(TextQuestion.order_number)
        ).scalars().all()
        
        for i, question in enumerate(text_questions):
            text_answer = db.session.execute(
                db.select(TextTestAnswer).where(
                    TextTestAnswer.test_result_id == test_result.id,
                    TextTestAnswer.text_question_id == question.id
                )
            ).scalar_one_or_none()
            
            user_answer = text_answer.user_answer if text_answer else ''
            is_correct = text_answer.is_correct if text_answer else False
            points_earned = text_answer.points_earned if text_answer else 0
            
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
        try:
            questions = json.loads(test.text_based_questions)
        except json.JSONDecodeError:
            questions = []
        
        user_answers = {}
        if test_result.answers:
            try:
                user_answers = json.loads(test_result.answers)
            except json.JSONDecodeError:
                user_answers = {}
        
        for i, question in enumerate(questions):
            question_key = f'question_{i}'
            user_answer = user_answers.get(question_key, '')
            
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
    
    correct_count = sum(1 for result in detailed_results if result['is_correct'])
    earned_points = sum(result['points_earned'] for result in detailed_results)
    
    if test.text_content_id:
        total_points = sum(result['question'].points if hasattr(result['question'], 'points') else 1 
                          for result in detailed_results)
    else:
        total_points = len(detailed_results)
    
    test_result.correct_answers = correct_count
    test_result.score = int((earned_points / total_points) * 100) if total_points > 0 else 0
    test_result.completed_at = datetime.utcnow()
    
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

@tests_bp.route('/details_data/<int:test_id>')
@require_login
@require_teacher
def test_details_data(test_id):
    user = get_current_user()
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
        else:
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
        'urls': {
            'test_results_base': url_for('tests.test_results', test_id=test.id, result_id=0)[:-1]
        }
    }
    return jsonify(data_to_return)

@tests_bp.route('/<test_link>/details')
@require_login
@require_teacher
def test_details_by_link(test_link):
    test = Test.query.filter_by(link=test_link).first_or_404()
    user = get_current_user()
    if test.created_by != user.id:
        abort(403)
    # Собрать данные для test_details.html
    students_in_class = User.query.filter_by(class_number=test.classs, teacher='no').all()
    total_students_in_class = len(students_in_class)
    all_results_for_test = TestResult.query.filter(
        TestResult.test_id == test.id,
        TestResult.started_at >= test.created_at
    ).all()
    completed_students_details = []
    in_progress_students_details = []
    not_started_students = []
    completed_students = set()
    in_progress_students = set()
    for result in all_results_for_test:
        if result.completed_at:
            completed_students.add(result.user_id)
            completed_students_details.append({'user': result.user, 'result': result})
        else:
            in_progress_students.add(result.user_id)
            in_progress_students_details.append({'user': result.user, 'result': result})
    all_class_user_ids = {u.id for u in students_in_class}
    not_started_ids = all_class_user_ids - completed_students - in_progress_students
    for uid in not_started_ids:
        s_user = db.session.get(User, uid)
        if s_user:
            not_started_students.append({'user': s_user})
    completed_count = len(completed_students_details)
    progress_percentage = (completed_count / total_students_in_class * 100) if total_students_in_class > 0 else 0
    return render_template('test_details.html',
        test=test,
        total_students_in_class=total_students_in_class,
        completed_students_details=completed_students_details,
        in_progress_students_details=in_progress_students_details,
        not_started_students=not_started_students,
        progress_percentage=progress_percentage,
        is_teacher=True
    )

@tests_bp.route('/test_details_data_by_link/<test_link>')
@require_login
@require_teacher
def test_details_data_by_link(test_link):
    test = Test.query.filter_by(link=test_link).first_or_404()
    user = get_current_user()
    if test.created_by != user.id:
        return jsonify({'error': 'Forbidden, not test creator'}), 403
    # Переиспользуем логику из test_details_data:
    students_in_class = User.query.filter_by(class_number=test.classs, teacher='no').all()
    total_students_in_class = len(students_in_class)
    all_results_for_test = TestResult.query.filter(
        TestResult.test_id == test.id,
        TestResult.started_at >= test.created_at
    ).all()
    completed_students_details_json = []
    in_progress_students_details_json = []
    not_started_students_json = []
    completed_students = set()
    in_progress_students = set()
    for result in all_results_for_test:
        if result.completed_at:
            completed_students.add(result.user_id)
            completed_students_details_json.append({'id': result.user_id, 'fio': result.user.fio, 'nick': result.user.nick})
        else:
            in_progress_students.add(result.user_id)
            in_progress_students_details_json.append({'id': result.user_id, 'fio': result.user.fio, 'nick': result.user.nick})
    all_class_user_ids = {u.id for u in students_in_class}
    not_started_ids = all_class_user_ids - completed_students - in_progress_students
    for uid in not_started_ids:
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
        'urls': {
            'test_results_base': url_for('tests.test_results', test_id=test.id, result_id=0)[:-1]
        }
    }
    return jsonify(data_to_return)

@tests_bp.route('/<int:test_id>/save_progress', methods=['POST'])
@require_login
def save_test_progress(test_id):
    user = get_current_user()
    test_result = TestResult.query.filter_by(
        test_id=test_id,
        user_id=user.id,
        completed_at=None
    ).first()
    
    if not test_result:
        return jsonify({'error': 'Active test not found'}), 404
    
    try:
        data = request.get_json()
        if not data or 'answers' not in data:
            return jsonify({'error': 'Invalid data format'}), 400
        
        for answer_data in data['answers']:
            test_word_id = answer_data.get('test_word_id')
            user_answer = answer_data.get('user_answer', '')
            
            if not test_word_id:
                continue
                
            test_word = TestWord.query.filter_by(id=test_word_id, test_id=test_id).first()
            if not test_word:
                continue
            
            progress = TestProgress.query.filter_by(
                test_result_id=test_result.id,
                test_word_id=test_word_id
            ).first()
            
            if progress:
                progress.user_answer = json.dumps(user_answer) if isinstance(user_answer, (dict, list)) else str(user_answer)
                progress.last_updated = datetime.utcnow()
            else:
                progress = TestProgress(
                    test_result_id=test_result.id,
                    test_word_id=test_word_id,
                    user_answer=json.dumps(user_answer) if isinstance(user_answer, (dict, list)) else str(user_answer)
                )
                db.session.add(progress)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Progress saved'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error saving progress: {str(e)}'}), 500

@tests_bp.route('/submit_test/<int:test_id>', methods=['POST'])
@require_login
def submit_test_proxy(test_id):
    """Proxy POST /tests/submit_test/<id> to the main application-level submit_test view.
    This avoids 404 when forms inside the tests blueprint post with a relative path.
    """
    from flask import current_app
    # Ensure the original view exists
    original_view = current_app.view_functions.get('submit_test')
    if original_view:
        return original_view(test_id)
    # Fallback: return 404 if not found
    return jsonify({'error': 'submit_test endpoint not available'}), 404


@tests_bp.route('/<int:test_id>/load_progress', methods=['GET'])
@require_login
def load_test_progress(test_id):
    user = get_current_user()
    test_result = TestResult.query.filter_by(
        test_id=test_id,
        user_id=user.id,
        completed_at=None
    ).first()
    
    if not test_result:
        return jsonify({'progress': {}})
    
    try:
        progress_entries = TestProgress.query.filter_by(
            test_result_id=test_result.id
        ).all()
        
        progress_data = {}
        for entry in progress_entries:
            try:
                user_answer = json.loads(entry.user_answer) if entry.user_answer else ''
            except (json.JSONDecodeError, TypeError):
                user_answer = entry.user_answer or ''
            
            progress_data[str(entry.test_word_id)] = user_answer
        
        return jsonify({'progress': progress_data})
        
    except Exception as e:
        return jsonify({'error': f'Error loading progress: {str(e)}'}), 500