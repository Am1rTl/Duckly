from markupsafe import escape
from flask import Flask, request, render_template, redirect, url_for, flash, make_response
from flask_sqlalchemy import SQLAlchemy
import base64 as bs64
import time
import sqlite3



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    fio = db.Column(db.String, nullable=False)
    nick = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    secret_key = db.Column(db.String, nullable=False)
    teacher = db.Column(db.String, nullable=True)

class Word(db.Model):
    __tablename__ = 'words'
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String, nullable=False)
    perevod = db.Column(db.String, nullable=False)
    classs = db.Column('class', db.String, nullable=False)
    unit = db.Column(db.String, nullable=False)

class Test(db.Model):
    __tablename__ = 'tests'
    classs = db.Column('class', db.String, primary_key=True)
    unit = db.Column(db.String, primary_key=True)
    type = db.Column(db.String, nullable=False)
    link = db.Column(db.String, unique=True, nullable=False)



@app.route("/")
def index():
    return redirect('/hello', 302)

@app.route("/user/<name>")
def greet(name):
    return f"Hello, {name}!"

@app.route("/profile")
def profile():
    reqinnone = 0
    user = None
    for cookie_name in request.cookies:
        user_obj = User.query.filter_by(nick=cookie_name).first()
        if user_obj:
            secret_key = bs64.b64encode(str.encode(user_obj.nick + user_obj.password[:2])).decode("utf-8")
            if request.cookies.get(cookie_name) == secret_key:
                user = user_obj
                break
            elif request.cookies.get(cookie_name) is not None:
                res = make_response(redirect('hello', 302))
                res.set_cookie(cookie_name, request.cookies.get(cookie_name), max_age=0)
                return res
    if user is None:
        return redirect('/login', 302)
    return render_template('profile.html', nick=user.nick, fio=user.fio)


@app.route("/add_tests", methods=['POST', 'GET'])
def add_tests():
    if request.method == "POST":
        classs = request.form['classSelect']
        print(classs, request.form)
        unit = request.form['unit']
        types = request.form['type']
        print(classs, unit, types)
        times = str(time.time()).split(".")
        link = times[0]+times[1]
        print(link)
        new_test = Test(classs=classs, unit=unit, type=types, link=link)
        db.session.add(new_test)
        db.session.commit()
        return redirect('/tests', 302)
    else:
        return render_template("add_tests.html")

@app.route("/tests")
def tests():
    reqinnone = 0
    user = None
    for cookie_name in request.cookies:
        user_obj = User.query.filter_by(nick=cookie_name).first()
        if user_obj:
            secret_key = bs64.b64encode(str.encode(user_obj.nick + user_obj.password[:2])).decode("utf-8")
            if request.cookies.get(cookie_name) == secret_key:
                user = user_obj
                break
            elif request.cookies.get(cookie_name) is not None:
                res = make_response(redirect('hello', 302))
                res.set_cookie(cookie_name, request.cookies.get(cookie_name), max_age=0)
                return res
    if user is None:
        return redirect('/login', 302)

    tests = Test.query.all()
    return render_template('tests.html', tests=tests)

@app.route("/tests/<id>", methods=['GET', 'POST'])
def test_id(id):
    user = None
    for cookie_name in request.cookies:
        user_obj = User.query.filter_by(nick=cookie_name).first()
        if user_obj:
            secret_key = bs64.b64encode(str.encode(user_obj.nick + user_obj.password[:2])).decode("utf-8")
            if request.cookies.get(cookie_name) == secret_key:
                user = user_obj
                break
            elif request.cookies.get(cookie_name) is not None:
                res = make_response(redirect('hello', 302))
                res.set_cookie(cookie_name, request.cookies.get(cookie_name), max_age=0)
                return res
    if user is None:
        return redirect('/login', 302)

    test = Test.query.filter_by(link=id).first()
    if not test:
        return "Test not found", 404

    classs = test.classs
    unit = test.unit
    test_type = test.type

    words = Word.query.filter_by(classs=classs, unit=unit).all()

    if request.method == 'POST':
        score = 0
        total = len(words)
        if test_type == 'dictation':
            for idx, word_obj in enumerate(words):
                answer = request.form.get(f'answer{idx}', '').strip().lower()
                if answer == word_obj.perevod.lower():
                    score += 1
        elif test_type == 'true_or_false':
            for idx, word_obj in enumerate(words):
                answer = request.form.get(f'answer{idx}', '').strip().lower()
                correct = 'true' if word_obj.perevod.lower() == 'true' else 'false'
                if answer == correct:
                    score += 1
        elif test_type == 'add_letter':
            for idx, word_obj in enumerate(words):
                answer = request.form.get(f'answer{idx}', '').strip().lower()
                if answer == word_obj.perevod.lower():
                    score += 1
        else:
            return "Unknown test type", 400

        return render_template('test_result.html', score=score, total=total, test_type=test_type)

    if test_type == 'dictation':
        return render_template('test_dictation.html', words=words, test_id=id)
    elif test_type == 'true_or_false':
        return render_template('test_true_or_false.html', words=words, test_id=id)
    elif test_type == 'add_letter':
        return render_template('test_add_letter.html', words=words, test_id=id)
    else:
        return "Unknown test type", 400

@app.route("/edit_profile")
def edit_profile():
    user = None
    for cookie_name in request.cookies:
        user_obj = User.query.filter_by(nick=cookie_name).first()
        if user_obj:
            secret_key = bs64.b64encode(str.encode(user_obj.nick + user_obj.password[:2])).decode("utf-8")
            if request.cookies.get(cookie_name) == secret_key:
                user = user_obj
                break
            elif request.cookies.get(cookie_name) is not None:
                res = make_response(redirect('hello', 302))
                res.set_cookie(cookie_name, request.cookies.get(cookie_name), max_age=0)
                return res
    if user is None:
        return redirect('/login', 302)
    return render_template('edit_profile.html', nick=user.nick, fio=user.fio)

@app.route("/save_profile", methods=["POST"])
def save_profile():
    fio = request.form.get("fio")
    nick = request.form.get("nick")

    user = User.query.filter_by(nick=nick).first()
    if user:
        user.fio = fio
        db.session.commit()

    return redirect("/profile")

@app.route("/add_words", methods=['POST', 'GET'])
def add_words():
    if request.method == "POST":
        classs = request.form['classSelect']
        unit = request.form['unitSelect']
        words = []
        perevods = []

        for key, value in request.form.items():
            if key.startswith("word"):
                words.append(value)
            elif key.startswith("perevod"):
                perevods.append(value)

        for word, perevod in zip(words, perevods):
            new_word = Word(word=word, perevod=perevod, classs=classs, unit=unit)
            db.session.add(new_word)
        db.session.commit()
        return redirect('/words', 302)

    return render_template("add_words.html")

@app.route('/words')
def words():
    words = Word.query.order_by(Word.classs).all()
    items = {}
    for w in words:
        if w.classs not in items:
            items[w.classs] = {}
        if w.unit not in items[w.classs]:
            items[w.classs][w.unit] = []
        items[w.classs][w.unit].append([w.word, w.perevod])

    return render_template("words.html", items=items)

@app.route('/login', methods=['POST', 'GET'])
def login():
    error = None
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(nick=username, password=password).first()
        if user:
            secret_key = bs64.b64encode(str.encode(username + password[:2])).decode("utf-8")
            resp = make_response(redirect('hello', 302))
            resp.set_cookie(username, secret_key, 60*60*24*15)
            return resp
        else:
            error = 'Invalid username/password'

    return render_template('login.html', error=error)

@app.route("/logout")
def logout():
    username = None
    for cookie_name in request.cookies:
        if User.query.filter_by(nick=cookie_name).first():
            username = cookie_name
            break
    if username:
        res = make_response(redirect('/login', 302))
        res.set_cookie(username, '', expires=0)
        return res
    else:
        return redirect('/login', 302)

@app.route('/registration', methods=['POST', 'GET'])
def registration():
    error = None
    if request.method == 'POST':
        fio = request.form["fio"]
        username = request.form['username']
        password = request.form['password']

        secret_key = bs64.b64encode(str.encode(username + password[:2])).decode("utf-8")

        max_id = db.session.query(db.func.max(User.id)).scalar()
        if max_id is None:
            max_id = 0
        else:
            max_id += 1

        existing_user = User.query.filter_by(nick=username).first()

        fio_in_mass = fio.split(' ')
        if len(fio_in_mass) == 3:
            if existing_user is None:
                new_user = User(fio=fio, nick=username, password=password, secret_key=secret_key, teacher='no', id=max_id)
                db.session.add(new_user)
                db.session.commit()
                resp = make_response(redirect('hello', 302))
                resp.set_cookie(username, secret_key, 60*60*24*15)
                return resp
            else:
                error = "Выбранный вами Username уже занят"
        else:
            error = "ФИО должно состоять из 3 слов"
    else:
        error = None

    return render_template('registration.html', error=error)

@app.route("/hello")
def hello():
    user = None
    for cookie_name in request.cookies:
        user_obj = User.query.filter_by(nick=cookie_name).first()
        if user_obj:
            secret_key = bs64.b64encode(str.encode(user_obj.nick + user_obj.password[:2])).decode("utf-8")
            if request.cookies.get(cookie_name) == secret_key:
                user = user_obj
                break
            elif request.cookies.get(cookie_name) is not None:
                res = make_response(redirect('hello', 302))
                res.set_cookie(cookie_name, request.cookies.get(cookie_name), max_age=0)
                return res
    if user is None:
        return redirect('/login', 302)

    fio_parts = user.fio.split(' ')
    try:
        letters = fio_parts[0][:1] + fio_parts[1][:1]
    except:
        letters = user.fio[0] + user.fio[1]

    return render_template('hello.html', username=user.nick, letters=letters)

@app.route("/about")
def about():
    return render_template("about.html")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
#    app.run("0.0.0.0")
    app.run(debug=True)
