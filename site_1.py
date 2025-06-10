from markupsafe import escape
from flask import Flask, jsonify, request, render_template, redirect, url_for, flash, make_response, session, abort, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from flask_session import Session
import random # Keep for main app if any randomization is done outside blueprints
import string # Keep for main app if any string ops are done outside blueprints
from datetime import datetime, timedelta
import json
import subprocess # For test.py execution, can be removed if test.py is not essential for startup
import re
import os
import tempfile

# Import models and db
from models import db, User, Word, Test, TestWord, TestResult, TestAnswer, TestProgress, UserWordReview, Sentence, TextContent, TextQuestion, TextTestAnswer

# Import Blueprints
from blueprints.auth import auth_bp
from blueprints.words import words_bp
from blueprints.games import games_bp
from blueprints.tests import tests_bp

# Shared Helper functions
def get_current_user():
    if 'user_id' not in session:
        return None
    return db.session.get(User, session['user_id'])

def require_login(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: # More direct check
            flash("Пожалуйста, войдите в систему для доступа к этой странице.", "warning")
            return redirect(url_for('auth_bp.login')) # Assuming auth_bp is the correct name
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def require_teacher(f):
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or user.teacher != 'yes':
            flash('Доступ запрещён. Требуются права учителя.', 'error')
            return redirect(url_for('hello'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

app = Flask(__name__)
try:
    os.makedirs(app.instance_path, exist_ok=True)
except OSError as e:
    print(f"Error creating instance directory {app.instance_path}: {e}")

if os.path.exists('/app'):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////app/instance/app.db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(app.instance_path, "app.db")}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'a-default-development-secret-key')

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=15)
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'duckly_'

if os.path.exists('/app'):
    session_dir = '/app/flask_session'
    if not os.path.exists(session_dir):
        os.makedirs(session_dir, exist_ok=True)
    app.config['SESSION_FILE_DIR'] = session_dir
else:
    app.config['SESSION_FILE_DIR'] = tempfile.gettempdir()

app.config['SESSION_COOKIE_NAME'] = 'duckly_session'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_PATH'] = '/'

Session(app)
db.init_app(app)

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(words_bp)
app.register_blueprint(games_bp, url_prefix='/games')
app.register_blueprint(tests_bp) # No prefix for tests_bp

@app.template_filter('from_json')
def from_json_filter(value):
    try:
        return json.loads(value) if value else []
    except (json.JSONDecodeError, TypeError):
        return []

# Core Routes
@app.route("/")
def index():
    return redirect(url_for('hello'))

@app.route("/user/<name>") # Example route, can be removed if not used
@require_login
def greet(name):
    # This is just an example, actual user greeting might be different
    return f"Hello, {escape(name)}!"

@app.route("/hello")
@require_login
def hello():
    user = get_current_user()
    letters = ''
    if user.fio:
        fio_parts = user.fio.split(' ')
        if len(fio_parts) >= 2:
            letters = (fio_parts[0][:1] + fio_parts[1][:1]).upper()
        elif len(fio_parts) == 1 and fio_parts[0]:
            letters = fio_parts[0][:2].upper() if len(fio_parts[0]) > 1 else fio_parts[0][0].upper()
        else:
            letters = user.nick[:2].upper() if user.nick else 'DU' # Default User
    else:
        letters = user.nick[:2].upper() if user.nick else 'DU'
    return render_template('hello.html', username=user.nick, letters=letters, current_user=user)

@app.route("/about")
def about():
    return render_template("about.html")

# Profile Management (Remains in site_1.py for now)
@app.route("/edit_profile")
@require_login
def edit_profile():
    user = get_current_user()
    return render_template('edit_profile.html', nick=user.nick, fio=user.fio, current_user=user)

@app.route("/save_profile", methods=["POST"])
@require_login
def save_profile():
    fio = request.form.get("fio")
    # nick = request.form.get("nick") # Usually nick is not changeable or has special handling
    user = get_current_user()
    if user:
        user.fio = fio
        db.session.commit()
        flash("Профиль обновлен.", "success")
    # Redirect to profile view (assuming auth_bp.profile or a similar route)
    return redirect(url_for('auth_bp.profile'))


# Utility AJAX routes (Shared or not yet moved)
@app.route("/get_units_for_class")
def get_units_for_class():
    class_name = request.args.get('class_name')
    if not class_name: return jsonify([])
    units = db.session.query(Word.unit).filter(Word.classs == class_name, Word.unit.isnot(None), Word.unit != '').distinct().order_by(Word.unit).all()
    return jsonify([unit[0] for unit in units if unit[0]])

@app.route("/get_modules_for_unit")
def get_modules_for_unit():
    class_name = request.args.get('class_name')
    unit_name = request.args.get('unit_name')
    if not class_name or not unit_name: return jsonify([])
    modules = db.session.query(Word.module).filter(Word.classs == class_name, Word.unit == unit_name, Word.module.isnot(None), Word.module != '').distinct().order_by(Word.module).all()
    return jsonify([module[0] for module in modules if module[0]])

@app.route('/get_word_count')
def get_word_count():
    class_name = request.args.get('class_name')
    unit_name = request.args.get('unit_name')
    module_name = request.args.get('module_name')
    units = request.args.getlist('units')
    modules = request.args.getlist('modules')
    if not class_name: return jsonify({'count': 0})
    query = Word.query.filter_by(classs=class_name)
    if units: query = query.filter(Word.unit.in_(units))
    elif unit_name:
        query = query.filter_by(unit=unit_name)
        if modules: query = query.filter(Word.module.in_(modules))
        elif module_name: query = query.filter_by(module=module_name)
    return jsonify({'count': query.count()})

@app.route("/get_modules_for_sentence_game")
def get_modules_for_sentence_game():
    class_name = request.args.get('class_name')
    unit_name = request.args.get('unit_name')
    if not class_name or not unit_name: return jsonify([])
    modules = db.session.query(Sentence.module).filter(Sentence.classs == class_name, Sentence.unit == unit_name).distinct().order_by(Sentence.module).all()
    return jsonify([module[0] for module in modules if module[0]])

# Granular add routes (potentially obsolete or for words_bp)
@app.route("/add_unit_to_class")
@require_login
@require_teacher
def add_unit_to_class_form():
    class_name = request.args.get("class")
    return f"""<h2>Добавить юнит в {class_name}</h2><form action="{url_for('save_unit')}" method="POST"><input type="hidden" name="class" value="{class_name}" /><input type="text" name="unit" placeholder="Название юнита" required /><button type="submit">Сохранить</button></form>"""

@app.route("/add_module_to_unit")
@require_login
@require_teacher
def add_module_to_unit_form():
    class_name = request.args.get("class")
    unit_name = request.args.get("unit")
    return f"""<h2>Добавить модуль в {unit_name} ({class_name})</h2><form action="{url_for('save_module')}" method="POST"><input type="hidden" name="class" value="{class_name}" /><input type="hidden" name="unit" value="{unit_name}" /><input type="text" name="module" placeholder="Название модуля" required /><button type="submit">Сохранить</button></form>"""

@app.route("/save_module", methods=["POST"])
@require_login
@require_teacher
def save_module():
    class_name = request.form.get("class")
    unit_name = request.form.get("unit")
    module_name = request.form.get("module")
    if class_name and unit_name and module_name:
        dummy_word = Word(word="dummy", perevod="заглушка", classs=class_name, unit=unit_name, module=module_name)
        db.session.add(dummy_word); db.session.commit()
    else:
        flash("Не удалось сохранить модуль, не все поля заполнены.", "error")
    return redirect(url_for('words_bp.words'))

@app.route("/add_word_to_module")
@require_login
@require_teacher
def add_word_to_module_form():
    class_name = request.args.get("class")
    unit_name = request.args.get("unit")
    module_name = request.args.get("module")
    return f"""<h2>Добавить слово в модуль: {module_name} ({unit_name}, {class_name})</h2><form action="{url_for('add_word')}" method="POST"><input type="hidden" name="class" value="{class_name}" /><input type="hidden" name="unit" value="{unit_name}" /><input type="hidden" name="module" value="{module_name}" /><label>Слово:</label><br/><input type="text" name="word" required /><br/><label>Перевод:</label><br/><input type="text" name="perevod" required /><br/><button type="submit">Добавить</button></form>"""

@app.route("/save_unit", methods=["POST"])
@require_login
@require_teacher
def save_unit():
    class_name = request.form.get("class")
    unit_name = request.form.get("unit")
    if class_name and unit_name:
        dummy_word = Word(word="dummy", perevod="заглушка", classs=class_name, unit=unit_name)
        db.session.add(dummy_word); db.session.commit()
    else:
        flash("Не удалось сохранить юнит, не все поля заполнены.", "error")
    return redirect(url_for('words_bp.words'))

@app.route("/add_word_to_unit")
@require_login
@require_teacher
def add_word_to_unit_form():
    class_name = request.args.get("class")
    unit_name = request.args.get("unit")
    return f"""<h2>Добавить слово в {unit_name} ({class_name})</h2><form action="{url_for('add_word')}" method="POST"><input type="hidden" name="class" value="{class_name}" /><input type="hidden" name="unit" value="{unit_name}" /><label>Слово:</label><br/><input type="text" name="word" required /><br/><label>Перевод:</label><br/><input type="text" name="perevod" required /><br/><button type="submit">Добавить</button></form>"""

@app.route("/add_word", methods=["POST"])
@require_login
@require_teacher
def add_word():
    class_name = request.form.get("class")
    unit_name = request.form.get("unit")
    module_name = request.form.get("module")
    word = request.form.get("word", "").strip()
    perevod = request.form.get("perevod", "").strip()
    if not all([class_name, unit_name, module_name, word, perevod]):
        flash("Невозможно добавить слово: необходимо заполнить все поля.", "error")
    else:
        new_word = Word(word=word, perevod=perevod, classs=class_name, unit=unit_name, module=module_name)
        db.session.add(new_word); db.session.commit()
        flash("Слово успешно добавлено.", "success")
    return redirect(url_for('words_bp.words'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if Sentence.query.count() == 0:
            sample_sentences = [
                Sentence(text="This is a simple sentence.", translation="Это простое предложение.", classs="5", unit="1", module="Greetings"),
                Sentence(text="The cat sleeps on the mat.", translation="Кошка спит на коврике.", classs="5", unit="1", module="Greetings"),
                Sentence(text="I like to learn English.", translation="Мне нравится учить английский.", classs="5", unit="1", module="School"),
                Sentence(text="She reads a book every day.", translation="Она читает книгу каждый день.", classs="6", unit="2", module="Hobbies"),
                Sentence(text="They play football in the park.", translation="Они играют в футбол в парке.", classs="6", unit="2", module="Hobbies")
            ]
            db.session.bulk_save_objects(sample_sentences)
            db.session.commit()
            print("Added sample sentences.")
        print("Database tables created (or already exist).")
    app.run("0.0.0.0", debug=True, port=1800)
