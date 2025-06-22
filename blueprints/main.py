from flask import Blueprint, render_template, redirect, url_for, session
from models import User

main_bp = Blueprint('main', __name__,
                    template_folder='../templates',
                    static_folder='../static')

@main_bp.route('/')
def index():
    # Redirect to login if not logged in, otherwise to hello page
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return redirect(url_for('main.hello'))

@main_bp.route('/hello')
def hello():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        # If user is not found, clear session and redirect to login
        session.clear()
        return redirect(url_for('auth.login'))
        
    return render_template('hello.html', user=user)

@main_bp.route('/greet/<name>')
def greet(name):
    return f"Hello, {name}!"
