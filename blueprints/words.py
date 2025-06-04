from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session

# Import models from models.py
from models import db, Word, User

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
