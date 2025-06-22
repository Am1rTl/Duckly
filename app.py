from flask import Flask, redirect, url_for, render_template
from flask_session import Session
from flask_caching import Cache
from datetime import timedelta
import os
from models import db
import subprocess
from config import Config

# Initialize Flask app
app = Flask(__name__)

# Load configuration
app.config.from_object(Config())

# Create instance folder if it doesn't exist
try:
    os.makedirs(app.instance_path, exist_ok=True)
except OSError as e:
    print(f"Error creating instance directory {app.instance_path}: {e}")

# Initialize database
db.init_app(app)

# Initialize session
Session(app)

# Initialize cache
cache = Cache(app)

# Create necessary directories
os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)

# Импорт и регистрация блюпринтов
from blueprints.auth import auth_bp
from blueprints.tests import tests_bp
from blueprints.words import words_bp
from blueprints.games import games_bp
from blueprints.quizlet import quizlet_bp
from blueprints.text_content import text_content_bp
from blueprints.profile import profile_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(tests_bp, url_prefix='/tests')
app.register_blueprint(words_bp, url_prefix='/words')
app.register_blueprint(games_bp, url_prefix='/games')
app.register_blueprint(quizlet_bp, url_prefix='/quizlet')
app.register_blueprint(text_content_bp, url_prefix='/text_content')
app.register_blueprint(profile_bp)

# Главная страница
@app.route("/")
def index():
    return redirect(url_for('tests.hello'))

# Обработчик ошибок
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Пользовательский фильтр
@app.template_filter('from_json')
def from_json_filter(value):
    try:
        return json.loads(value) if value else []
    except (json.JSONDecodeError, TypeError):
        return []

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # Добавление тестовых предложений
        from models import Sentence
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
        print("Database tables created (or already exist). Running test.py...")
        try:
            subprocess.run(["python", "test.py"], check=True, capture_output=True, text=True)
            print("test.py executed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error running test.py: {e}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
    app.run("0.0.0.0", debug=True, port=1800)