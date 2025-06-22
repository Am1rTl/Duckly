from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
from blueprints.utils import get_current_user, require_login

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(nick=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Successfully logged in!', 'success')
            return redirect(url_for('tests.hello'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        fio = request.form.get('fio')
        class_number = request.form.get('class_number')
        teacher = request.form.get('teacher', 'no')
        
        if User.query.filter_by(nick=username).first():
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        user = User(
            nick=username,
            password=generate_password_hash(password),
            fio=fio,
            class_number=class_number,
            teacher=teacher
        )
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth_bp.route('/logout')
@require_login
def logout():
    session.pop('user_id', None)
    session.pop('active_test_result_id', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('auth.login'))
