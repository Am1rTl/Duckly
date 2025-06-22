from flask import Blueprint, render_template
from models import Word
from blueprints.utils import require_login

quizlet_bp = Blueprint('quizlet', __name__)


@quizlet_bp.route('/<class_name>/<unit_name>/<module_name>')
@require_login
def quizlet_cards(class_name, unit_name, module_name):
    """Render flashcards (quizlet-style) for a given class / unit / module."""
    words_db = (
        Word.query
        .filter_by(classs=class_name, unit=unit_name, module=module_name)
        .order_by(Word.word)
        .all()
    )
    words = [{"word": w.word, "perevod": w.perevod} for w in words_db]
    return render_template(
        'quizlet_cards.html',
        words=words,
        class_name=class_name,
        unit_name=unit_name,
        module_name=module_name,
    )
