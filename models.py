from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nick = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    fio = db.Column(db.String(100), nullable=False)
    class_number = db.Column(db.String(10), nullable=False)
    teacher = db.Column(db.String(3), default='no')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Word(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), nullable=False)
    perevod = db.Column(db.String(100), nullable=False)
    classs = db.Column(db.String(10), nullable=False)
    unit = db.Column(db.String(50), nullable=False)
    module = db.Column(db.String(100), nullable=False)

class Sentence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    translation = db.Column(db.Text, nullable=False)
    classs = db.Column(db.String(10), nullable=False)
    unit = db.Column(db.String(50), nullable=False)
    module = db.Column(db.String(100), nullable=False)

class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    classs = db.Column(db.String(10), nullable=False)
    unit = db.Column(db.String(50))
    module = db.Column(db.String(100))
    type = db.Column(db.String(50), nullable=False)
    test_direction = db.Column(db.String(50), default='word_to_translation')
    text_content = db.Column(db.Text)
    text_content_id = db.Column(db.Integer, db.ForeignKey('text_content.id'))
    text_based_questions = db.Column(db.Text)
    link = db.Column(db.String(50), unique=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    time_limit = db.Column(db.Integer)
    word_count = db.Column(db.Integer)
    word_order = db.Column(db.String(20), default='sequential')
    test_mode = db.Column(db.String(50))
    dictation_word_source = db.Column(db.String(50))
    dictation_selected_words = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

class TestWord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    word = db.Column(db.String(200), nullable=False)
    perevod = db.Column(db.String(200), nullable=False)
    correct_answer = db.Column(db.String(200), nullable=False)
    options = db.Column(db.Text)
    missing_letters = db.Column(db.Text)
    word_order = db.Column(db.Integer, nullable=False)

class TestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, default=0)
    correct_answers = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)
    answers = db.Column(db.Text)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    time_taken = db.Column(db.Integer)

class TestAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_result_id = db.Column(db.Integer, db.ForeignKey('test_result.id'), nullable=False)
    test_word_id = db.Column(db.Integer, db.ForeignKey('test_word.id'), nullable=False)
    user_answer = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

class TextContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    classs = db.Column(db.String(10), nullable=False)
    unit = db.Column(db.String(50))
    module = db.Column(db.String(100))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TextQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text_content_id = db.Column(db.Integer, db.ForeignKey('text_content.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), nullable=False)
    correct_answer = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text)
    points = db.Column(db.Integer, default=1)
    order_number = db.Column(db.Integer, nullable=False)

class TextTestAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_result_id = db.Column(db.Integer, db.ForeignKey('test_result.id'), nullable=False)
    text_question_id = db.Column(db.Integer, db.ForeignKey('text_question.id'), nullable=False)
    user_answer = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    points_earned = db.Column(db.Integer, default=0)

class UserWordReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    word_id = db.Column(db.Integer, db.ForeignKey('word.id'), nullable=False)
    interval_days = db.Column(db.Integer, default=0)
    ease_factor = db.Column(db.Float, default=2.5)
    last_reviewed_at = db.Column(db.DateTime)
    next_review_at = db.Column(db.DateTime)

class TestProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_result_id = db.Column(db.Integer, db.ForeignKey('test_result.id'), nullable=False)
    test_word_id = db.Column(db.Integer, db.ForeignKey('test_word.id'), nullable=False)
    user_answer = db.Column(db.Text)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)