from flask import Blueprint, jsonify, request, render_template
from models import db, Word
from blueprints.utils import get_current_user, require_login

words_bp = Blueprint('words', __name__)

@words_bp.route('/')
@require_login
def words_home():
    """Render human-readable words page"""
    # Build nested dict of words similar to front-end expectation
    words = Word.query.order_by(Word.classs, Word.unit, Word.module, Word.word).all()
    data = {}
    for w in words:
        data.setdefault(w.classs, {}).setdefault(w.unit, {}).setdefault(w.module, []).append({
            "id": w.id,
            "word": w.word,
            "perevod": w.perevod
        })
    class_names = sorted(data.keys())
    user = get_current_user()
    is_teacher = bool(user and user.teacher == 'yes')
    return render_template('words.html', items=data, class_names=class_names, is_teacher=is_teacher)

@words_bp.route('/json')
@require_login
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

@words_bp.route('/for_module_selection')
@require_login
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
                            "text": f"{mw.word} - {mw.perevod}"
                        })
                        seen_word_ids.add(mw.id)
            except Exception as e:
                print(f"Error fetching words for module {module_identifier}: {e}")
                pass
        else:
            print(f"Invalid module identifier format: {module_identifier}")
            pass
            
    return jsonify({"words": words_list})

# Route to display words for a specific module (accessible at /words/class/<class>/<unit>/<module>)
@words_bp.route('/class/<class_name>/<unit_name>/<module_name>')
@require_login
def module_words(class_name, unit_name, module_name):
    """Render words belonging to a particular class/unit/module grouping."""
    words = Word.query.filter_by(classs=class_name, unit=unit_name, module=module_name).order_by(Word.word).all()
    return render_template(
        'module_words.html',
        words=words,
        class_name=class_name,
        unit_name=unit_name,
        module_name=module_name
    )