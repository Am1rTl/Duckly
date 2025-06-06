from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session

import uuid # For generating unique test links
from datetime import datetime # For created_at if not using db.func
# Import models from models.py
from models import db, Word, User, Test, TestWord # Added TestWord model

words_bp = Blueprint('words', __name__,
                     template_folder='../templates',
                     static_folder='../static',
                     static_url_path='/words/static') # Example

@words_bp.route("/words/json")
def get_words_json():
    # This route might be better if it's authenticated or if public access is intended
    words = Word.query.all()
    data = {}
    for w in words:
        if w.classs not in data:
            data[w.classs] = {}
        if w.unit not in data[w.classs]:
            data[w.classs][w.unit] = []
        data[w.classs][w.unit].append([w.word, w.perevod])
    return jsonify(data)

@words_bp.route("/get_units_for_class")
def get_units_for_class():
    class_name = request.args.get('class_name')
    if not class_name:
        return jsonify([])

    units = db.session.query(Word.unit).filter(
        Word.classs == class_name
    ).distinct().order_by(Word.unit).all() # Added order_by for consistency

    return jsonify([unit[0] for unit in units if unit[0]]) # Filter out None/empty

@words_bp.route("/get_modules_for_unit")
def get_modules_for_unit():
    class_name = request.args.get('class_name')
    unit_name = request.args.get('unit_name')

    if not class_name or not unit_name:
        return jsonify([])

    modules = db.session.query(Word.module).filter(
        Word.classs == class_name,
        Word.unit == unit_name
    ).distinct().order_by(Word.module).all() # Added order_by

    return jsonify([module[0] for module in modules if module[0]]) # Filter out None/empty

@words_bp.route('/words')
def words():
    # Check if user is logged in and get their role
    is_teacher = False
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and user.teacher == 'yes':
            is_teacher = True
    
    all_words = Word.query.order_by(Word.classs, Word.unit, Word.module, Word.word).all()
    items = {}

    for w in all_words:
        if w.classs not in items:
            items[w.classs] = {}
        if w.unit not in items[w.classs]:
            items[w.classs][w.unit] = {}
        if w.module not in items[w.classs][w.unit]:
            items[w.classs][w.unit][w.module] = []
        items[w.classs][w.unit][w.module].append({'id': w.id, 'word': w.word, 'perevod': w.perevod}) # Pass id for edit/delete

    return render_template("words.html", items=items, is_teacher=is_teacher)

@words_bp.route("/add_words", methods=['POST', 'GET'])
def add_words():
    if 'user_id' not in session: # Basic auth check
        flash("Пожалуйста, войдите в систему для добавления слов.", "warning")
        return redirect(url_for('auth.login'))

    # Teacher check - only teachers can add words
    user = User.query.get(session['user_id'])
    if not user or user.teacher != 'yes':
        flash("Только учителя могут добавлять слова.", "warning")
        return redirect(url_for('words.words'))


    if request.method == "POST":
        class_val = request.form.get('classSelect')
        unit_val = request.form.get('unitSelect')
        module_val = request.form.get('moduleSelect')

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

        classs = classs if classs else "DefaultClass" # Ensure defaults if empty
        unit = unit if unit else "DefaultUnit"
        module = module if module else "DefaultModule"


        words_input = request.form.getlist("word[]") # Assuming form names are word[] and perevod[]
        perevods_input = request.form.getlist("perevod[]")

        # Filter out empty pairs
        added_count = 0
        for word_text, perevod_text in zip(words_input, perevods_input):
            word_text = word_text.strip()
            perevod_text = perevod_text.strip()
            if word_text and perevod_text: # Only add if both are non-empty
                # Check for duplicates within the same class, unit, module
                existing_word = Word.query.filter_by(
                    word=word_text,
                    classs=classs,
                    unit=unit,
                    module=module
                ).first()
                if not existing_word:
                    new_word = Word(word=word_text, perevod=perevod_text, classs=classs, unit=unit, module=module)
                    db.session.add(new_word)
                    added_count += 1
                else:
                    flash(f"Слово '{word_text}' уже существует в этом модуле. Пропущено.", "info")

        if added_count > 0:
            try:
                db.session.commit()
                flash(f"Успешно добавлено {added_count} слов(а).", "success")
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка при добавлении слов: {str(e)}", "error")
        elif not any(w.strip() and p.strip() for w, p in zip(words_input, perevods_input)):
             flash("Не было введено слов для добавления.", "info")

        return redirect(url_for('words.words')) # Adjusted for blueprint

    # GET method: query existing classes for dropdown
    classes_query = db.session.query(Word.classs).distinct().order_by(Word.classs).all()
    classes = [c[0] for c in classes_query if c[0]]
    return render_template("add_words.html", classes=classes)


@words_bp.route('/edit_word/<int:word_id>', methods=['GET', 'POST'])
def edit_word(word_id):
    # Add login check and teacher check
    if 'user_id' not in session:
        flash("Пожалуйста, войдите в систему.", "warning")
        return redirect(url_for('auth.login'))
    
    # Teacher check - only teachers can edit words
    user = User.query.get(session['user_id'])
    if not user or user.teacher != 'yes':
        flash("Только учителя могут редактировать слова.", "warning")
        return redirect(url_for('words.words'))

    word_obj = Word.query.get_or_404(word_id)

    if request.method == 'POST':
        new_word_text = request.form.get('word', '').strip()
        new_perevod = request.form.get('perevod', '').strip()
        selected_class = request.form.get('classSelect')
        selected_unit_option = request.form.get('unitSelect')
        selected_module_option = request.form.get('moduleSelect')

        new_class = selected_class
        new_unit = selected_unit_option
        new_module = selected_module_option

        if selected_unit_option == 'add_new_unit':
            new_unit = request.form.get('newUnitInput', '').strip()
        if selected_module_option == 'add_new_module':
            new_module = request.form.get('newModuleInput', '').strip()

        if not new_word_text or not new_perevod or not new_class or not new_unit: # Module can be empty string
            flash("Слово, перевод, класс и юнит не могут быть пустыми.", "error")
            # Pass necessary data back to template for re-rendering
            all_classes = [c[0] for c in db.session.query(Word.classs).distinct().order_by(Word.classs).all() if c[0]]
            # For units and modules, we'd ideally pass what's relevant to the current word's class/unit
            # or make the JS reload them. Simpler for now:
            current_units = [u[0] for u in db.session.query(Word.unit).filter_by(classs=word_obj.classs).distinct().all() if u[0]]
            current_modules = [m[0] for m in db.session.query(Word.module).filter_by(classs=word_obj.classs, unit=word_obj.unit).distinct().all() if m[0]]
            return render_template('edit_word.html', word=word_obj, all_classes=all_classes, current_units=current_units, current_modules=current_modules)

        # Check for duplicates if critical fields are changed
        if (new_word_text != word_obj.word or
            new_class != word_obj.classs or
            new_unit != word_obj.unit or
            new_module != word_obj.module):
            existing_word = Word.query.filter(
                Word.id != word_obj.id, # Exclude self
                Word.word == new_word_text,
                Word.classs == new_class,
                Word.unit == new_unit,
                Word.module == new_module
            ).first()
            if existing_word:
                flash(f"Слово '{new_word_text}' уже существует в этом классе/юните/модуле.", "error")
                all_classes = [c[0] for c in db.session.query(Word.classs).distinct().order_by(Word.classs).all() if c[0]]
                current_units = [u[0] for u in db.session.query(Word.unit).filter_by(classs=word_obj.classs).distinct().all() if u[0]]
                current_modules = [m[0] for m in db.session.query(Word.module).filter_by(classs=word_obj.classs, unit=word_obj.unit).distinct().all() if m[0]]
                return render_template('edit_word.html', word=word_obj, all_classes=all_classes, current_units=current_units, current_modules=current_modules)

        word_obj.word = new_word_text
        word_obj.perevod = new_perevod
        word_obj.classs = new_class
        word_obj.unit = new_unit
        word_obj.module = new_module if new_module is not None else ""

        try:
            db.session.commit()
            flash("Слово успешно обновлено!", "success")
            return redirect(url_for('words.words', _anchor=f"word-{word_obj.id}"))
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при обновлении слова: {str(e)}", "error")
            # Fall through to render template again

    all_classes = [c[0] for c in db.session.query(Word.classs).distinct().order_by(Word.classs).all() if c[0]]
    current_units = [u[0] for u in db.session.query(Word.unit).filter_by(classs=word_obj.classs).distinct().all() if u[0]]
    current_modules = [m[0] for m in db.session.query(Word.module).filter_by(classs=word_obj.classs, unit=word_obj.unit).distinct().all() if m[0]]

    return render_template('edit_word.html',
                           word=word_obj,
                           all_classes=all_classes,
                           current_class=word_obj.classs,
                           current_unit=word_obj.unit,
                           current_module=word_obj.module,
                           current_units_for_class=current_units,
                           current_modules_for_unit=current_modules
                           )


@words_bp.route('/delete_word/<int:word_id>', methods=['POST'])
def delete_word(word_id):
    if 'user_id' not in session:
         return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    # Teacher check - only teachers can delete words
    user = User.query.get(session['user_id'])
    if not user or user.teacher != 'yes':
        return jsonify({'success': False, 'error': 'Only teachers can delete words'}), 403

    word_obj = Word.query.get_or_404(word_id)

    try:
        db.session.delete(word_obj)
        db.session.commit()
        flash("Слово успешно удалено.", "success") # Flash for next request
        return jsonify({'success': True, 'message': 'Слово удалено'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@words_bp.route('/class/<class_name>/<unit_name>/<module_name>')
def module_words(class_name, unit_name, module_name):
    # Add login check if these pages are not public
    module_words_list = Word.query.filter_by(classs=class_name, unit=unit_name, module=module_name).order_by(Word.word).all()
    return render_template('module_words.html',
                         words=module_words_list,
                         class_name=class_name,
                         unit_name=unit_name,
                         module_name=module_name)

@words_bp.route('/quizlet/<class_name>/<unit_name>/<module_name>')
def quizlet_cards(class_name, unit_name, module_name):
    # Add login check if these pages are not public
    word_objects = Word.query.filter_by(classs=class_name, unit=unit_name, module=module_name).all()

    words_for_template = [{'id': word.id, 'word': word.word, 'perevod': word.perevod,
                           'classs': word.classs, 'unit': word.unit, 'module': word.module}
                          for word in word_objects]
    return render_template('quizlet_cards.html',
                         words=words_for_template,
                         class_name=class_name,
                         unit_name=unit_name,
                         module_name=module_name)


@words_bp.route('/create_test', methods=['GET', 'POST'])
def create_test():
    if 'user_id' not in session:
        flash("Пожалуйста, войдите в систему, чтобы создавать тесты.", "warning")
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    if not user or user.teacher != 'yes':
        flash("Только учителя могут создавать тесты.", "error")
        return redirect(url_for('words.words')) # Or a more appropriate page

    if request.method == 'POST':
        title = request.form.get('title')
        class_number = request.form.get('class_number') # Form uses class_number
        test_type = request.form.get('test_type') # Form uses test_type
        time_limit_str = request.form.get('time_limit', '0')
        word_order = request.form.get('word_order')
        word_count_str = request.form.get('word_count')

        # Fields specific to certain test types
        test_mode = request.form.get('test_mode') # For add_letter
        dictation_word_source = request.form.get('dictation_word_source') # For dictation
        # dictation_random_word_count = request.form.get('dictation_random_word_count') # Not directly on Test model

        text_content = None
        if test_type == 'text_based':
            text_content = request.form.get('text_content')

        if not title or not class_number or not test_type or not word_order:
            flash("Необходимо заполнить все обязательные поля: Название, Класс, Тип теста, Порядок слов.", "error")
            return redirect(url_for('words.create_test')) # Redirect back to form

        try:
            time_limit = int(time_limit_str) if time_limit_str else 0
            word_count = int(word_count_str) if word_count_str and word_count_str.isdigit() else None
        except ValueError:
            flash("Лимит времени и количество слов должны быть числами.", "error")
            return redirect(url_for('words.create_test'))

        # Generate a unique link for the test
        unique_link = str(uuid.uuid4())

        new_test = Test(
            title=title,
            classs=class_number, # Model uses 'classs'
            type=test_type,      # Model uses 'type'
            link=unique_link,
            created_by=user.id,
            time_limit=time_limit if time_limit > 0 else None,
            word_order=word_order,
            word_count=word_count if word_count and word_count > 0 else None,
            test_mode=test_mode if test_type == 'add_letter' else None,
            text_content=text_content if test_type == 'text_based' else None,
            dictation_word_source=dictation_word_source if test_type == 'dictation' else None,
            is_active=True # Default to active, can be changed later
            # unit, module, dictation_selected_words will be set when words are configured
        )

        try:
            db.session.add(new_test)
            db.session.commit()
            flash(f"Тест '{new_test.title}' успешно создан. Теперь добавьте слова и настройте тест.", "success")
            # Redirect to a new route for configuring words for this test
            # For now, redirecting to a placeholder or back to tests list.
            # This will eventually be something like: url_for('words.configure_test_words', test_id=new_test.id)
            return redirect(url_for('words.words')) # Placeholder redirect
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при создании теста: {str(e)}", "error")
            return redirect(url_for('words.create_test'))

    # GET request: render the form
    return render_template('create_test.html')

@words_bp.route('/configure_text_questions/<int:test_id>', methods=['GET', 'POST'])
def configure_text_questions(test_id):
    if 'user_id' not in session:
        flash("Пожалуйста, войдите в систему.", "warning")
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    if not user or user.teacher != 'yes':
        flash("Только учителя могут настраивать вопросы теста.", "error")
        return redirect(url_for('words.words')) # Or a general access denied page

    test = Test.query.get_or_404(test_id)

    if test.type != 'text_based':
        flash("Этот тест не является текстовым тестом.", "error")
        return redirect(url_for('words.words')) # Or redirect to a page showing test details

    if test.created_by != user.id:
        # Optional: If only the creator can edit. Could also allow other teachers.
        flash("Вы не являетесь создателем этого теста.", "error")
        return redirect(url_for('words.words'))


    if request.method == 'POST':
        question_text = request.form.get('question_text','').strip()
        options_list = request.form.getlist('options[]') # Assuming options are named 'options[]'
        correct_options_indices = request.form.getlist('correct_options[]') # Indices of correct options
        question_type = request.form.get('question_type') # 'single' or 'multiple'

        # Basic validation
        if not question_text:
            flash("Текст вопроса не может быть пустым.", "error")
            return redirect(url_for('words.configure_text_questions', test_id=test_id))

        cleaned_options = [opt.strip() for opt in options_list if opt.strip()]
        if len(cleaned_options) < 2: # Need at least two options
            flash("Необходимо предоставить как минимум два варианта ответа.", "error")
            return redirect(url_for('words.configure_text_questions', test_id=test_id))

        if not correct_options_indices:
            flash("Необходимо отметить хотя бы один правильный ответ.", "error")
            return redirect(url_for('words.configure_text_questions', test_id=test_id))

        if question_type == 'single' and len(correct_options_indices) > 1:
            flash("Для вопроса с одним правильным ответом может быть выбран только один вариант.", "error")
            return redirect(url_for('words.configure_text_questions', test_id=test_id))

        correct_answers_text = [cleaned_options[int(i)] for i in correct_options_indices]

        # Determine word_order for the new question
        last_test_word = TestWord.query.filter_by(test_id=test.id).order_by(TestWord.word_order.desc()).first()
        new_word_order = (last_test_word.word_order + 1) if last_test_word else 1

        new_question = TestWord(
            test_id=test.id,
            word=question_text, # Using 'word' field for the question itself
            options=jsonify(cleaned_options).get_data(as_text=True), # Store options as JSON string
            correct_answer=jsonify(correct_answers_text).get_data(as_text=True), # Store correct answers as JSON array
            question_type=question_type,
            perevod="", # Not used for text_based questions, or could be a hint
            word_order=new_word_order
        )

        try:
            db.session.add(new_question)
            db.session.commit()
            flash("Вопрос успешно добавлен.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при добавлении вопроса: {str(e)}", "error")

        return redirect(url_for('words.configure_text_questions', test_id=test_id))

    # GET request
    existing_questions = TestWord.query.filter_by(test_id=test_id).order_by(TestWord.word_order).all()
    return render_template('configure_text_questions.html', test=test, questions=existing_questions)
