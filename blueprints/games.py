from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from models import db, Word, UserWordReview, Sentence, User # Added User import
import random
from datetime import datetime, timedelta
from site_1 import get_current_user, require_login # Import shared helpers

games_bp = Blueprint('games_bp', __name__, template_folder='../templates', static_folder='../static')

@games_bp.route('/') # This will be accessible at /games/
@require_login
def games_home():
    user = get_current_user() # Use imported helper
    if not user: # Should be handled by @require_login, but defensive
        flash("Пользователь не найден, пожалуйста, войдите снова.", "error")
        return redirect(url_for('auth_bp.login'))
    return render_template('games.html', is_teacher=user.teacher == 'yes', current_user=user)

@games_bp.route('/flashcards/select', methods=['GET'])
@require_login
def flashcards_select_module():
    # Fetch all unique classes for the first dropdown
    classes = db.session.query(Word.classs).distinct().order_by(Word.classs).all()
    classes = [c[0] for c in classes if c[0]] # Ensure not None or empty
    return render_template('game_flashcards_select_improved.html', classes=classes)

@games_bp.route('/flashcards/<class_name>/<unit_name>/<module_name>')
@games_bp.route('/flashcards/<class_name>/<unit_name>')
@games_bp.route('/flashcards/<class_name>')
@require_login
def flashcards_game(class_name, unit_name=None, module_name=None):
    user_id = session['user_id']

    mode = request.args.get('mode', 'specific')
    cards_count = int(request.args.get('cards', 0))
    selected_modules_str = request.args.get('modules', '')
    selected_units_str = request.args.get('units', '')
    selected_modules = selected_modules_str.split(',') if selected_modules_str else []
    selected_units = selected_units_str.split(',') if selected_units_str else []

    words_in_module = []
    display_info = ""

    query = Word.query.filter(Word.classs == class_name)

    if mode == 'specific' and unit_name and module_name:
        query = query.filter(Word.unit == unit_name, Word.module == module_name)
        display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модуль: {module_name}"
    elif mode == 'unit' and unit_name:
        query = query.filter(Word.unit == unit_name)
        display_info = f"Класс: {class_name}, Юнит: {unit_name} (все модули)"
    elif mode == 'class':
        display_info = f"Класс: {class_name} (все юниты и модули)"
    elif mode == 'multiple-modules' and unit_name and selected_modules:
        query = query.filter(Word.unit == unit_name, Word.module.in_(selected_modules))
        display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модули: {', '.join(selected_modules)}"
    elif mode == 'multiple-units' and selected_units:
        query = query.filter(Word.unit.in_(selected_units))
        display_info = f"Класс: {class_name}, Юниты: {', '.join(selected_units)}"
    else: # Fallback or invalid mode for context
        if unit_name and module_name: # Default to specific if parts of it are provided
             query = query.filter(Word.unit == unit_name, Word.module == module_name)
             display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модуль: {module_name}"
        else:
            flash("Неверные параметры игры для флэш-карточек.", "warning")
            return redirect(url_for('.flashcards_select_module')) # Use . for current blueprint

    words_in_module = query.all()

    if not words_in_module:
        flash(f"Для выбранных параметров не найдено слов (Флэш-карточки).", "warning")
        return redirect(url_for('.flashcards_select_module'))

    augmented_words_list = []
    now = datetime.utcnow()

    for word_obj in words_in_module:
        review_data = UserWordReview.query.filter_by(user_id=user_id, word_id=word_obj.id).first()
        is_new = review_data is None
        next_review_at_iso = None
        interval = None
        is_due = True # Default for new cards or if review_data is missing

        if review_data:
            next_review_at_iso = review_data.next_review_at.isoformat()
            interval = review_data.interval_days
            is_due = review_data.next_review_at <= now

        augmented_words_list.append({
            'id': word_obj.id, 'word': word_obj.word, 'perevod': word_obj.perevod,
            'classs': word_obj.classs, 'unit': word_obj.unit, 'module': word_obj.module,
            'next_review_at': next_review_at_iso, 'interval_days': interval,
            'is_new': is_new, 'is_due': is_due
        })

    augmented_words_list.sort(key=lambda x: (
        not x['is_due'], x['next_review_at'] is None,
        x['next_review_at'] if x['next_review_at'] else now.isoformat(), x['id']
    ))

    if cards_count > 0 and len(augmented_words_list) > cards_count:
        augmented_words_list = augmented_words_list[:cards_count]

    if not augmented_words_list:
        flash(f"Не найдено подходящих слов для флэш-карточек после фильтрации.", "warning")
        return redirect(url_for('.flashcards_select_module'))

    return render_template('game_flashcards_improved.html',
                           words=augmented_words_list, class_name=class_name,
                           unit_name=unit_name or "Все юниты", module_name=module_name or "Все модули",
                           display_info=display_info, total_cards=len(augmented_words_list), game_mode=mode)

@games_bp.route('/flashcards/update_review', methods=['POST'])
@require_login
def update_flashcard_review():
    if 'user_id' not in session: # Should be caught by @require_login, but defensive
        return jsonify({'error': 'Unauthorized', 'success': False}), 401

    data = request.get_json()
    word_id = data.get('word_id')
    quality = data.get('quality')

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

    if quality < 2:
        review_item.interval_days = 1
        if quality == 0:
             review_item.ease_factor = max(1.3, review_item.ease_factor - 0.2)
        elif quality == 1:
             review_item.ease_factor = max(1.3, review_item.ease_factor - 0.15)
    elif quality == 2:
        if review_item.interval_days == 0:
            review_item.interval_days = 1
        elif review_item.interval_days == 1:
             review_item.interval_days = 6
        else:
            review_item.interval_days = round(review_item.interval_days * review_item.ease_factor)
    elif quality == 3:
        if review_item.interval_days == 0:
            review_item.interval_days = 4
        elif review_item.interval_days == 1:
             review_item.interval_days = 10
        else:
            review_item.interval_days = round(review_item.interval_days * review_item.ease_factor * 1.3)
        review_item.ease_factor = min(3.0, review_item.ease_factor + 0.15)

    review_item.interval_days = min(review_item.interval_days, 365)
    review_item.next_review_at = datetime.utcnow() + timedelta(days=review_item.interval_days)
    review_item.last_reviewed_at = datetime.utcnow()

    try:
        db.session.commit()
        return jsonify({
            'success': True, 'next_review_in_days': review_item.interval_days,
            'next_review_date': review_item.next_review_at.isoformat(),
            'ease_factor': review_item.ease_factor
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database commit failed', 'details': str(e), 'success': False}), 500

@games_bp.route('/word_match/select', methods=['GET'])
@require_login
def word_match_select_module():
    classes = db.session.query(Word.classs).distinct().order_by(Word.classs).all()
    classes = [c[0] for c in classes if c[0]]
    return render_template('game_word_match_select_improved.html', classes=classes)

@games_bp.route('/word_match/<class_name>/<unit_name>/<module_name>')
@games_bp.route('/word_match/<class_name>/<unit_name>')
@games_bp.route('/word_match/<class_name>')
@require_login
def word_match_game(class_name, unit_name=None, module_name=None):
    mode = request.args.get('mode', 'specific')
    cards_count = int(request.args.get('cards', 8))
    timer_duration = int(request.args.get('timer', 0))
    enable_stopwatch = request.args.get('stopwatch') == 'true'
    selected_modules_str = request.args.get('modules', '')
    selected_units_str = request.args.get('units', '')
    selected_modules = selected_modules_str.split(',') if selected_modules_str else []
    selected_units = selected_units_str.split(',') if selected_units_str else []

    all_words = []
    display_info = ""
    query = Word.query.filter(Word.classs == class_name)

    if mode == 'specific' and unit_name and module_name:
        query = query.filter(Word.unit == unit_name, Word.module == module_name)
        display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модуль: {module_name}"
    elif mode == 'unit' and unit_name:
        query = query.filter(Word.unit == unit_name)
        display_info = f"Класс: {class_name}, Юнит: {unit_name} (все модули)"
    elif mode == 'class':
        display_info = f"Класс: {class_name} (все юниты и модули)"
    elif mode == 'multiple-modules' and unit_name and selected_modules:
        query = query.filter(Word.unit == unit_name, Word.module.in_(selected_modules))
        display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модули: {', '.join(selected_modules)}"
    elif mode == 'multiple-units' and selected_units:
        query = query.filter(Word.unit.in_(selected_units))
        display_info = f"Класс: {class_name}, Юниты: {', '.join(selected_units)}"
    else: # Fallback
        if unit_name and module_name:
             query = query.filter(Word.unit == unit_name, Word.module == module_name)
             display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модуль: {module_name}"
        else:
            flash("Неверные параметры игры 'Найди пару'.", "warning")
            return redirect(url_for('.word_match_select_module'))

    all_words = query.all()

    if not all_words:
        flash(f"Для выбранных параметров не найдено слов ('Найди пару').", "warning")
        return redirect(url_for('.word_match_select_module'))

    max_pairs = len(all_words)
    num_pairs = min(cards_count, max_pairs)

    if num_pairs < 2:
        flash(f"Недостаточно слов для игры 'Найди пару' (нужно хотя бы 2, найдено {max_pairs}).", "warning")
        return redirect(url_for('.word_match_select_module'))

    selected_word_objects = random.sample(all_words, num_pairs)
    original_words_for_js = [{'id': w.id, 'word': w.word, 'translation': w.perevod} for w in selected_word_objects]
    jumbled_words_list = [{'id': w.id, 'text': w.word} for w in selected_word_objects]
    jumbled_translations_list = [{'id': w.id, 'text': w.perevod} for w in selected_word_objects]
    random.shuffle(jumbled_words_list)
    random.shuffle(jumbled_translations_list)

    return render_template('game_word_match.html',
                           original_words=original_words_for_js,
                           jumbled_words_list=jumbled_words_list,
                           jumbled_translations_list=jumbled_translations_list,
                           class_name=class_name, unit_name=unit_name or "Все юниты",
                           module_name=module_name or "Все модули", display_info=display_info,
                           num_pairs=num_pairs, timer_duration=timer_duration,
                           enable_stopwatch=enable_stopwatch, game_mode=mode)

@games_bp.route('/sentence_scramble/select', methods=['GET'])
@require_login
def sentence_scramble_select_module():
    classes = db.session.query(Sentence.classs).distinct().order_by(Sentence.classs).all()
    classes = [c[0] for c in classes if c[0]]
    return render_template('game_sentence_scramble_select.html', classes=classes)

@games_bp.route('/sentence_scramble/<class_name>/<unit_name>/<module_name>')
@require_login
def sentence_scramble_game(class_name, unit_name, module_name):
    sentences_query = Sentence.query.filter_by(classs=class_name, unit=unit_name, module=module_name).all()
    if not sentences_query:
        flash(f"Для модуля '{module_name}' (юнит '{unit_name}', класс '{class_name}') не найдено предложений.", "warning")
        return redirect(url_for('.sentence_scramble_select_module'))

    sentences_for_js = [{'id': s.id, 'text': s.text, 'translation': s.translation} for s in sentences_query]
    random.shuffle(sentences_for_js)

    return render_template('game_sentence_scramble.html',
                           sentences=sentences_for_js, class_name=class_name,
                           unit_name=unit_name, module_name=module_name)

@games_bp.route('/hangman/select', methods=['GET'])
@require_login
def hangman_select_module():
    classes = db.session.query(Word.classs).distinct().order_by(Word.classs).all()
    classes = [c[0] for c in classes if c[0]]
    return render_template('game_hangman_select_improved.html', classes=classes)

@games_bp.route('/hangman/<class_name>/<unit_name>/<module_name>')
@require_login
def hangman_game(class_name, unit_name, module_name):
    num_words = int(request.args.get('words', 10))
    timer_duration = int(request.args.get('timer', 0))
    enable_stopwatch = request.args.get('stopwatch', 'false').lower() == 'true'
    difficulty = request.args.get('difficulty', 'medium')
    game_mode = request.args.get('mode', 'specific')
    selected_modules_str = request.args.get('modules', '')
    selected_modules = selected_modules_str.split(',') if selected_modules_str else []

    words_query_list = []
    query = Word.query.filter(Word.classs == class_name)

    if game_mode == 'unit':
        query = query.filter(Word.unit == unit_name)
    elif game_mode == 'class':
        pass # Already filtered by class
    elif game_mode == 'multiple' and unit_name and selected_modules: # Assuming multiple modules are within the same unit for simplicity here
        query = query.filter(Word.unit == unit_name, Word.module.in_(selected_modules))
    elif game_mode == 'specific': # Default to specific module
        query = query.filter(Word.unit == unit_name, Word.module == module_name)
    else: # Fallback for invalid mode or incomplete params
        flash("Неверный режим игры 'Виселица'.", "warning")
        return redirect(url_for('.hangman_select_module'))

    words_query_list = query.all()

    if not words_query_list:
        flash(f"Для выбранных параметров не найдено слов ('Виселица').", "warning")
        return redirect(url_for('.hangman_select_module'))

    if difficulty == 'easy': words_query_list = [w for w in words_query_list if 3 <= len(w.word) <= 5]
    elif difficulty == 'medium': words_query_list = [w for w in words_query_list if 4 <= len(w.word) <= 8]
    elif difficulty == 'hard': words_query_list = [w for w in words_query_list if len(w.word) >= 6]

    if not words_query_list:
        flash(f"Для выбранной сложности не найдено подходящих слов ('Виселица').", "warning")
        return redirect(url_for('.hangman_select_module'))

    if len(words_query_list) > num_words:
        words_query_list = random.sample(words_query_list, num_words)
    else:
        random.shuffle(words_query_list)

    game_words = [{'id': w.id, 'word': w.word.upper(), 'translation': w.perevod,
                   'definition': getattr(w, 'definition', ''), 'example': getattr(w, 'example', '')}
                  for w in words_query_list]

    return render_template('game_hangman_improved.html',
                           words_data=game_words, class_name=class_name, unit_name=unit_name,
                           module_name=module_name, timer_duration=timer_duration,
                           enable_stopwatch=enable_stopwatch, difficulty=difficulty,
                           game_mode=game_mode, num_words=len(game_words))

# Need to import require_login from the main app or a shared utils module
# For now, assuming it's accessible globally, or adjust imports as needed.
# Example: from site_1 import require_login (if it remains in site_1.py)
# Or: from .utils import require_login (if moved to a utils.py in blueprints folder)
# Removed placeholder for require_login and User class, as they are imported or available via models
