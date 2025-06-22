from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta

# Import db and User from models
from models import db, User

auth_bp = Blueprint('auth', __name__,
                    template_folder='../templates',
                    static_folder='../static',
                    static_url_path='/auth/static') # Example static path for blueprint if needed

@auth_bp.route('/login', methods=['POST', 'GET'])
def login():
    error = None
    if request.method == "POST":
        username = request.form['username']
        password_form = request.form['password']

        if username == 'teacher':
            teacher_user = User.query.filter_by(nick='teacher').first()
            if teacher_user and check_password_hash(teacher_user.password, password_form):
                session['user_id'] = teacher_user.id
                session.permanent = True
                current_app.permanent_session_lifetime = timedelta(days=15)
                return redirect(url_for('hello')) # 'hello' might need to be 'main.hello' if it also moves
            elif not teacher_user and password_form == 'teacher':
                hashed_password = generate_password_hash('teacher')
                teacher = User(
                    fio='Teacher',
                    nick='teacher',
                    password=hashed_password,
                    teacher='yes'
                )
                db.session.add(teacher)
                db.session.commit()
                session['user_id'] = teacher.id
                session.permanent = True
                current_app.permanent_session_lifetime = timedelta(days=15)
 return redirect(url_for('main.hello')) # 'hello' might need to be 'main.hello' if it also moves
            else:
                error = 'Invalid teacher credentials'
        else:
            user = User.query.filter_by(nick=username).first()
            if user and check_password_hash(user.password, password_form):
                session['user_id'] = user.id
                session.permanent = True
                current_app.permanent_session_lifetime = timedelta(days=15)
 return redirect(url_for('main.hello'))
            else:
                error = 'Invalid username/password'

    return render_template('login.html', error=error)

@auth_bp.route("/logout")
def logout():
    session.pop('user_id', None)
    flash("Вы успешно вышли из системы.", "info")
    return redirect(url_for('auth.login')) # Adjusted for blueprint

@auth_bp.route('/registration', methods=['POST', 'GET'])
def registration():
    error = None
    if request.method == 'POST':
        fio = request.form["fio"]
        username = request.form['username']
        password = request.form['password']
        password_confirm = request.form.get('password_confirm')
        class_number = request.form.get('class_number')

        if not class_number:
            error = "Please select a class"
            return render_template('registration.html', error=error, classes=[str(i) for i in range(1, 12)], fio=fio, username=username)

        if password != password_confirm:
            error = "Пароли не совпадают"
            return render_template('registration.html', error=error, fio=fio, username=username, selected_class=class_number, classes=[str(i) for i in range(1, 12)])

        existing_user = User.query.filter_by(nick=username).first()
        if existing_user:
            error = "Выбранный вами Username уже занят"
            return render_template('registration.html', error=error, fio=fio, username=username, selected_class=class_number, classes=[str(i) for i in range(1, 12)])

        fio_in_mass = fio.split(' ')
        if len(fio_in_mass) != 3:
            error = "ФИО должно состоять из 3 слов"
            return render_template('registration.html', error=error, fio=fio, username=username, selected_class=class_number, classes=[str(i) for i in range(1, 12)])

        hashed_password = generate_password_hash(password)

        new_user = User(
            fio=fio,
            nick=username,
            password=hashed_password,
            teacher='no',
            class_number=class_number
        )
        db.session.add(new_user)
        db.session.commit()

        session['user_id'] = new_user.id
        session.permanent = True
        current_app.permanent_session_lifetime = timedelta(days=15)
 flash("Регистрация прошла успешно! Вы вошли в систему.", "success")
        return redirect(url_for('hello'))

    classes = [str(i) for i in range(1, 12)]
    return render_template('registration.html', error=error, classes=classes)

@auth_bp.route("/profile")
def profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    if not user:
        session.pop('user_id', None)
        flash("Пользователь не найден, пожалуйста, войдите снова.", "error")
        return redirect(url_for('auth.login'))

    return render_template('profile.html', nick=user.nick, fio=user.fio)

@auth_bp.route("/edit_profile")
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    if not user:
        session.pop('user_id', None)
        flash("Пользователь не найден, пожалуйста, войдите снова.", "error")
        return redirect(url_for('auth.login'))

    return render_template('edit_profile.html', nick=user.nick, fio=user.fio)

@auth_bp.route("/save_profile", methods=["POST"])
def save_profile():
    if 'user_id' not in session: # Added protection
        flash("Сначала войдите в систему.", "warning")
        return redirect(url_for('auth.login'))

    fio = request.form.get("fio")
    nick = request.form.get("nick") # Assuming nick cannot be changed, or if it can, need to check for uniqueness if it's different from current user's nick

    user = User.query.get(session['user_id']) # Get user by ID from session
    if user:
        # Check if nick is being changed and if the new nick is already taken by someone else
        if nick != user.nick:
            existing_user_with_new_nick = User.query.filter(User.nick == nick, User.id != user.id).first()
            if existing_user_with_new_nick:
                flash("Этот никнейм уже занят другим пользователем.", "error")
                return redirect(url_for('auth.edit_profile'))
            user.nick = nick

        user.fio = fio
        db.session.commit()
        flash("Профиль успешно обновлен.", "success")
    else:
        flash("Пользователь не найден.", "error")
        return redirect(url_for('auth.login'))

    return redirect(url_for('auth.profile'))
