from flask import session, flash, redirect, url_for
from functools import wraps
from models import db, User  # Импортируем db и User из models.py

def get_current_user():
    """Безопасное получение текущего пользователя с использованием современного API SQLAlchemy"""
    if 'user_id' not in session:
        return None
    return db.session.get(User, session['user_id'])

def require_login(f):
    """Декоратор для проверки авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите, чтобы получить доступ к этой странице.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def require_teacher(f):
    """Декоратор для проверки прав учителя"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or user.teacher != 'yes':
            flash('Доступ запрещён. Требуются права учителя.', 'error')
            return redirect(url_for('main.hello'))  # Используем 'main' для главной страницы
        return f(*args, **kwargs)
    return decorated_function
