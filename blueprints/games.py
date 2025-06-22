from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash, session
from models import db, Word, Sentence, UserWordReview
from blueprints.utils import get_current_user, require_login
from datetime import datetime, timedelta
import random
import json

games_bp = Blueprint('games', __name__)

@games_bp.route('/')
@require_login
def games():
    user = get_current_user()
    return render_template('games.html', is_teacher=user.teacher == 'yes')

@games_bp.route('/flashcards/select', methods=['GET'])
@require_login
def flashcards_select_module():
    classes = db.session.query(Word.classs).distinct().order_by(Word.classs).all()
    classes = [c[0] for c in classes if c[0]]
    return render_template('game_flashcards_select_improved.html', classes=classes)

@games_bp.route('/flashcards/<class_name>/<unit_name>/<module_name>')
@games_bp.route('/flashcards/<class_name>/<unit_name>')
@games_bp.route('/flashcards/<class_name>')
@require_login
def flashcards_game(class_name, unit_name=None, module_name=None):
    user_id = session['user_id']
    mode = request.args.get('mode', 'specific')
    cards_count = int(request.args.get('cards', 0))
    selected_modules = request.args.get('modules', '').split(',') if request.args.get('modules') else []
    selected_units = request.args.get('units', '').split(',') if request.args.get('units') else []
    
    words_in_module = []
    
    if mode == 'specific' and unit_name and module_name:
        words_in_module = Word.query.filter_by(classs=class_name, unit=unit_name, module=module_name).all()
        display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модуль: {module_name}"
    elif mode == 'unit' and unit_name:
        words_in_module = Word.query.filter_by(classs=class_name, unit=unit_name).all()
        display_info = f"Класс: {class_name}, Юнит: {unit_name} (все модули)"
    elif mode == 'class':
        words_in_module = Word.query.filter_by(classs=class_name).all()
        display_info = f"Класс: {class_name} (все юниты и модули)"
    elif mode == 'multiple-modules' and unit_name and selected_modules:
        words_in_module = Word.query.filter(
            Word.classs == class_name,
            Word.unit == unit_name,
            Word.module.in_(selected_modules)
        ).all()
        display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модули: {', '.join(selected_modules)}"
    elif mode == 'multiple-units' and selected_units:
        words_in_module = Word.query.filter(
            Word.classs == class_name,
            Word.unit.in_(selected_units)
        ).all()
        display_info = f"Класс: {class_name}, Юниты: {', '.join(selected_units)}"
    else:
        if unit_name and module_name:
            words_in_module = Word.query.filter_by(classs=class_name, unit=unit_name, module=module_name).all()
            display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модуль: {module_name}"
        else:
            flash("Invalid game parameters.", "warning")
            return redirect(url_for('games.flashcards_select_module'))

    if not words_in_module:
        flash(f"No words found for the selected parameters.", "warning")
        return redirect(url_for('games.flashcards_select_module'))

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
        else:
            is_due = True

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
            'is_due': is_due
        })

    augmented_words_list.sort(key=lambda x: (
        not x['is_due'],
        x['next_review_at'] is None,
        x['next_review_at'] if x['next_review_at'] else now.isoformat(),
        x['id']
    ))

    if cards_count > 0 and len(augmented_words_list) > cards_count:
        augmented_words_list = augmented_words_list[:cards_count]

    if not augmented_words_list:
        flash(f"No words found for the selected parameters.", "warning")
        return redirect(url_for('games.flashcards_select_module'))

    return render_template('game_flashcards_improved.html',
                           words=augmented_words_list,
                           class_name=class_name,
                           unit_name=unit_name or "Все юниты",
                           module_name=module_name or "Все модули",
                           display_info=display_info,
                           total_cards=len(augmented_words_list),
                           game_mode=mode)

@games_bp.route('/flashcards/update_review', methods=['POST'])
@require_login
def update_flashcard_review():
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
            'success': True,
            'next_review_in_days': review_item.interval_days,
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
    selected_modules = request.args.get('modules', '').split(',') if request.args.get('modules') else []
    selected_units = request.args.get('units', '').split(',') if request.args.get('units') else []

    all_words = []
    
    if mode == 'specific' and unit_name and module_name:
        all_words = Word.query.filter_by(classs=class_name, unit=unit_name, module=module_name).all()
        display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модуль: {module_name}"
    elif mode == 'unit' and unit_name:
        all_words = Word.query.filter_by(classs=class_name, unit=unit_name).all()
        display_info = f"Класс: {class_name}, Юнит: {unit_name} (все модули)"
    elif mode == 'class':
        all_words = Word.query.filter_by(classs=class_name).all()
        display_info = f"Класс: {class_name} (все юниты и модули)"
    elif mode == 'multiple-modules' and unit_name and selected_modules:
        all_words = Word.query.filter(
            Word.classs == class_name,
            Word.unit == unit_name,
            Word.module.in_(selected_modules)
        ).all()
        display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модули: {', '.join(selected_modules)}"
    elif mode == 'multiple-units' and selected_units:
        all_words = Word.query.filter(
            Word.classs == class_name,
            Word.unit.in_(selected_units)
        ).all()
        display_info = f"Класс: {class_name}, Юниты: {', '.join(selected_units)}"
    else:
        if unit_name and module_name:
            all_words = Word.query.filter_by(classs=class_name, unit=unit_name, module=module_name).all()
            display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модуль: {module_name}"
        else:
            flash("Invalid game parameters.", "warning")
            return redirect(url_for('games.word_match_select_module'))

    if not all_words:
        flash(f"No words found for the selected parameters.", "warning")
        return redirect(url_for('games.word_match_select_module'))

    max_pairs = len(all_words)
    if cards_count > max_pairs:
        cards_count = max_pairs

    if cards_count < 1:
        flash("Not enough words to start the game.", "warning")
        return redirect(url_for('games.word_match_select_module'))

    random.shuffle(all_words)
    selected_words = all_words[:cards_count]
    word_pairs = [{'word': w.word, 'perevod': w.perevod} for w in selected_words]

    return render_template('game_word_match.html',
                           word_pairs=word_pairs,
                           class_name=class_name,
                           unit_name=unit_name or "Все юниты",
                           module_name=module_name or "Все модули",
                           display_info=display_info,
                           total_pairs=len(word_pairs),
                           timer_duration=timer_duration,
                           enable_stopwatch=enable_stopwatch,
                           game_mode=mode)

@games_bp.route('/hangman/select', methods=['GET'])
@require_login
def hangman_select_module():
    classes = db.session.query(Word.classs).distinct().order_by(Word.classs).all()
    classes = [c[0] for c in classes if c[0]]
    return render_template('game_hangman_select.html', classes=classes)

@games_bp.route('/hangman/<class_name>/<unit_name>/<module_name>')
@games_bp.route('/hangman/<class_name>/<unit_name>')
@games_bp.route('/hangman/<class_name>')
@require_login
def hangman_game(class_name, unit_name=None, module_name=None):
    mode = request.args.get('mode', 'specific')
    selected_modules = request.args.get('modules', '').split(',') if request.args.get('modules') else []
    selected_units = request.args.get('units', '').split(',') if request.args.get('units') else []

    all_words = []
    
    if mode == 'specific' and unit_name and module_name:
        all_words = Word.query.filter_by(classs=class_name, unit=unit_name, module=module_name).all()
        display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модуль: {module_name}"
    elif mode == 'unit' and unit_name:
        all_words = Word.query.filter_by(classs=class_name, unit=unit_name).all()
        display_info = f"Класс: {class_name}, Юнит: {unit_name} (все модули)"
    elif mode == 'class':
        all_words = Word.query.filter_by(classs=class_name).all()
        display_info = f"Класс: {class_name} (все юниты и модули)"
    elif mode == 'multiple-modules' and unit_name and selected_modules:
        all_words = Word.query.filter(
            Word.classs == class_name,
            Word.unit == unit_name,
            Word.module.in_(selected_modules)
        ).all()
        display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модули: {', '.join(selected_modules)}"
    elif mode == 'multiple-units' and selected_units:
        all_words = Word.query.filter(
            Word.classs == class_name,
            Word.unit.in_(selected_units)
        ).all()
        display_info = f"Класс: {class_name}, Юниты: {', '.join(selected_units)}"
    else:
        if unit_name and module_name:
            all_words = Word.query.filter_by(classs=class_name, unit=unit_name, module=module_name).all()
            display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модуль: {module_name}"
        else:
            flash("Invalid game parameters.", "warning")
            return redirect(url_for('games.hangman_select_module'))

    if not all_words:
        flash(f"No words found for the selected parameters.", "warning")
        return redirect(url_for('games.hangman_select_module'))

    selected_word = random.choice(all_words)
    word_data = {
        'word': selected_word.word,
        'hint': selected_word.perevod
    }

    return render_template('game_hangman.html',
                           word_data=word_data,
                           class_name=class_name,
                           unit_name=unit_name or "Все юниты",
                           module_name=module_name or "Все модули",
                           display_info=display_info,
                           game_mode=mode)

@games_bp.route('/sentence_scramble/select', methods=['GET'])
@require_login
def sentence_scramble_select_module():
    classes = db.session.query(Sentence.classs).distinct().order_by(Sentence.classs).all()
    classes = [c[0] for c in classes if c[0]]
    return render_template('game_sentence_scramble_select.html', classes=classes)

@games_bp.route('/sentence_scramble/<class_name>/<unit_name>/<module_name>')
@games_bp.route('/sentence_scramble/<class_name>/<unit_name>')
@games_bp.route('/sentence_scramble/<class_name>')
@require_login
def sentence_scramble_game(class_name, unit_name=None, module_name=None):
    mode = request.args.get('mode', 'specific')
    sentence_count = int(request.args.get('sentences', 5))
    selected_modules = request.args.get('modules', '').split(',') if request.args.get('modules') else []
    selected_units = request.args.get('units', '').split(',') if request.args.get('units') else []

    all_sentences = []
    
    if mode == 'specific' and unit_name and module_name:
        all_sentences = Sentence.query.filter_by(classs=class_name, unit=unit_name, module=module_name).all()
        display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модуль: {module_name}"
    elif mode == 'unit' and unit_name:
        all_sentences = Sentence.query.filter_by(classs=class_name, unit=unit_name).all()
        display_info = f"Класс: {class_name}, Юнит: {unit_name} (все модули)"
    elif mode == 'class':
        all_sentences = Sentence.query.filter_by(classs=class_name).all()
        display_info = f"Класс: {class_name} (все юниты и модули)"
    elif mode == 'multiple-modules' and unit_name and selected_modules:
        all_sentences = Sentence.query.filter(
            Sentence.classs == class_name,
            Sentence.unit == unit_name,
            Sentence.module.in_(selected_modules)
        ).all()
        display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модули: {', '.join(selected_modules)}"
    elif mode == 'multiple-units' and selected_units:
        all_sentences = Sentence.query.filter(
            Sentence.classs == class_name,
            Sentence.unit.in_(selected_units)
        ).all()
        display_info = f"Класс: {class_name}, Юниты: {', '.join(selected_units)}"
    else:
        if unit_name and module_name:
            all_sentences = Sentence.query.filter_by(classs=class_name, unit=unit_name, module=module_name).all()
            display_info = f"Класс: {class_name}, Юнит: {unit_name}, Модуль: {module_name}"
        else:
            flash("Invalid game parameters.", "warning")
            return redirect(url_for('games.sentence_scramble_select_module'))

    if not all_sentences:
        flash(f"No sentences found for the selected parameters.", "warning")
        return redirect(url_for('games.sentence_scramble_select_module'))

    max_sentences = len(all_sentences)
    if sentence_count > max_sentences:
        sentence_count = max_sentences

    random.shuffle(all_sentences)
    selected_sentences = all_sentences[:sentence_count]
    sentence_data = []
    for sentence in selected_sentences:
        words = sentence.text.split()
        random.shuffle(words)
        sentence_data.append({
            'original': sentence.text,
            'translation': sentence.translation,
            'scrambled': words
        })

    return render_template('game_sentence_scramble.html',
                           sentences=sentence_data,
                           class_name=class_name,
                           unit_name=unit_name or "Все юниты",
                           module_name=module_name or "Все модули",
                           display_info=display_info,
                           total_sentences=len(sentence_data),
                           game_mode=mode)