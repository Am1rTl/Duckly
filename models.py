from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

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
    # Добавить в класс Test:
    test_direction = db.Column(db.String(20), default='word_to_translation')  # 'word_to_translation' или 'translation_to_word'
    text_content = db.Column(db.Text)  # Для загруженного текста (deprecated, используйте text_content_id)
    text_based_questions = db.Column(db.Text)  # JSON с вопросами по тексту (deprecated, используйте text_content_id)
    text_content_id = db.Column(db.Integer, db.ForeignKey('text_contents.id'), nullable=True)  # Связь с текстовым контентом



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

class TestProgress(db.Model):
    __tablename__ = 'test_progress'
    id = db.Column(db.Integer, primary_key=True)
    test_result_id = db.Column(db.Integer, db.ForeignKey('test_results.id'), nullable=False)
    test_word_id = db.Column(db.Integer, db.ForeignKey('test_words.id'), nullable=False)
    user_answer = db.Column(db.Text, nullable=True)  # JSON string for complex answers like dictation

class TextContent(db.Model):
    """Модель для хранения текстов"""
    __tablename__ = 'text_contents'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    classs = db.Column('class', db.String, nullable=False)
    unit = db.Column(db.String, nullable=True)
    module = db.Column(db.String, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    questions = db.relationship('TextQuestion', backref='text_content', lazy=True, cascade='all, delete-orphan')
    tests = db.relationship('Test', backref='text_content_ref', lazy=True)

class TextQuestion(db.Model):
    """Модель для вопросов к текстам"""
    __tablename__ = 'text_questions'
    id = db.Column(db.Integer, primary_key=True)
    text_content_id = db.Column(db.Integer, db.ForeignKey('text_contents.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), nullable=False)  # 'multiple_choice', 'open_answer', 'true_false', 'multiple_select'
    options = db.Column(db.Text, nullable=True)  # JSON для вариантов ответов
    correct_answer = db.Column(db.Text, nullable=False)  # Для multiple_select - JSON массив правильных ответов
    points = db.Column(db.Integer, default=1)
    order_number = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class TextTestAnswer(db.Model):
    """Модель для ответов на вопросы текстовых тестов"""
    __tablename__ = 'text_test_answers'
    id = db.Column(db.Integer, primary_key=True)
    test_result_id = db.Column(db.Integer, db.ForeignKey('test_results.id'), nullable=False)
    text_question_id = db.Column(db.Integer, db.ForeignKey('text_questions.id'), nullable=False)
    user_answer = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, nullable=False, default=False)
    points_earned = db.Column(db.Integer, default=0)
    answered_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # Relationships
    text_question = db.relationship('TextQuestion', backref=db.backref('answers', lazy=True))
    test_result = db.relationship('TestResult', backref=db.backref('text_answers', lazy=True))
    
    # Unique constraint to ensure one answer per test_result and text_question
    __table_args__ = (db.UniqueConstraint('test_result_id', 'text_question_id', name='_text_test_answer_uc'),)

class UserWordReview(db.Model):
    __tablename__ = 'user_word_reviews'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    word_id = db.Column(db.Integer, db.ForeignKey('words.id'), nullable=False)
    next_review_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    interval_days = db.Column(db.Integer, default=0) # Current interval in days
    ease_factor = db.Column(db.Float, default=2.5) # Standard SM-2 starting ease
    last_reviewed_at = db.Column(db.DateTime, nullable=True)
    # Add unique constraint for user_id and word_id
    __table_args__ = (db.UniqueConstraint('user_id', 'word_id', name='_user_word_uc'),)

    user = db.relationship('User', backref=db.backref('reviews', lazy='dynamic'))
    word = db.relationship('Word', backref=db.backref('reviews', lazy='dynamic'))

class Sentence(db.Model):
    __tablename__ = 'sentences'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String, nullable=False) # The English sentence
    translation = db.Column(db.String, nullable=True) # Russian translation
    classs = db.Column(db.String, nullable=False)
    unit = db.Column(db.String, nullable=False)
    module = db.Column(db.String, nullable=False)
    # Potentially add difficulty level later