from markupsafe import escape
from flask import Flask, request, render_template
import sqlite3
import base64 as bs64
from flask import Flask, render_template, request, redirect, url_for, flash, make_response




app = Flask(__name__)



@app.route("/")
def index():
    return redirect('/hello', 301)

@app.route("/user/<name>")
def greet(name):
    return f"Hello, {name}!"

@app.route("/profile")
def profile():
    reqinnone = 0
    con = sqlite3.connect('app.db')
    cur = con.cursor()
    res = cur.execute('''SELECT nick FROM users;''')
    res = res.fetchall()
    for i in res:
        query = f'''SELECT password FROM users WHERE nick='{i[0]}';'''
        passwd = cur.execute(query)
        passwd = passwd.fetchall()
        passwd = passwd[0]
        secret_key = bs64.b64encode(str.encode(i[0]+passwd[0][:2])).decode("utf-8") 
        ##print('"'+str(request.cookies.get(i[0]))+'"','"'+secret_key+'"')
        if request.cookies.get(i[0]) == secret_key:

            query = f'''SELECT fio FROM users WHERE nick='{i[0]}';'''
            fio = cur.execute(query)
            fio = fio.fetchall()
            fio = fio[0][0]
            print(fio)

            return render_template('profile.html', nick=i[0], fio=fio)
        elif request.cookies.get(i[0]) != None:
            res = make_response(redirect('hello', 301))
            res.set_cookie(i[0], request.cookies.get(i[0]), max_age=0)
            return res
        elif request.cookies.get(i[0]) == None:
            reqinnone == None
    if reqinnone == None:
        return redirect('/login', 301)
    return render_template("profile.html")



@app.route("/add_words", methods=['POST', 'GET'])
def add_words():
    if request.method == "POST":
        unit = request.form['unit']
        classs = request.form['class']
        words = []
        perevods = []

        # Loop through all form fields and extract the word and perevod values
        for key, value in request.form.items():
            if key.startswith("word"):
                words.append(value)
            elif key.startswith("perevod"):
                perevods.append(value)

        # Print the captured words and perevods
        for word, perevod in zip(words, perevods):
            print(word, perevod, unit, classs)

            con = sqlite3.connect('app.db')
            cur = con.cursor()
            res = cur.execute('''SELECT MAX(id) FROM words;''')
            max_id = res.fetchone()
            max_id = max_id[0] + 1

            query = f'''INSERT INTO words (word, perevod, class, unit, id) VALUES ('{word}', '{perevod}', '{classs}', '{unit}', '{max_id}');'''
            cur.execute(query)
            con.commit()
            con.close()

    return render_template("add_words.html")


@app.route('/words')
def words():
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    query = "SELECT word, perevod, class, unit FROM words ORDER BY class"
    cursor.execute(query)
    data = cursor.fetchall()
    print(data)
    conn.close()
    items = {}
    for i in data:
        try:
            tmp = items[i[2]]
        except:
            items[i[2]] = {}

        try:
            items[i[2]][i[3]].append([i[0],i[1]])
        except:
            items[i[2]][i[3]] = []
            items[i[2]][i[3]].append([i[0],i[1]])


    print(items)
    #for item in list(items.keys()):
    #    print(item)


    return render_template("words.html", items=items)


@app.route('/login', methods=['POST', 'GET'])
def login():
    error = None
    try:
        if request.method == "POST":
            username = request.form['username']
            password = request.form['password']

            con = sqlite3.connect('app.db')
            cur = con.cursor()
            query = f'''SELECT id FROM users WHERE nick='{username}' AND password='{password}' ;'''
            print(query)
            ids = cur.execute(query)
            ids = ids.fetchall()
            print(ids)
            if ids != []:
                ids = ids[0][0]
                print(ids)


        if request.method == 'POST' and ids != []:
            print("Username: "+request.form['username'])
            print("Password: "+request.form['password'])
            print(username+password[:2])
            secret_key = bs64.b64encode(str.encode(username+password[:2])).decode("utf-8") 

            resp = make_response(redirect('hello', 301))
            resp.set_cookie(username, secret_key, 60*60*24*15)
            return resp
    except:
        print("I have problem")

    if request.method == "POST":
        error = 'Invalid username/password'
    # the code below is executed if the request method
    # was GET or the credentials were invalid
    return render_template('login.html', error=error)


@app.route('/registration', methods=['POST', 'GET'])
def registration():
    error = None
    if request.method == 'POST':
        print("FIO: "+request.form["fio"])
        fio = request.form["fio"]
        print("Username: "+request.form['username'])
        username = request.form['username']
        print("Password: "+request.form['password'])
        password = request.form['password']

        secret_key = bs64.b64encode(str.encode(username+password[:2])).decode("utf-8") 
        print(secret_key)

        try:
            con = sqlite3.connect('app.db')
            cur = con.cursor()
            res = cur.execute('''SELECT MAX(id) FROM users''')
            res = res.fetchone()
            print(res)
            res = res[0]
            max_id = res+1
        except:
            con = sqlite3.connect('app.db')
            cur = con.cursor()
            max_id = 0

        query = f'''SELECT id FROM users WHERE nick='{username}' '''
        res = cur.execute(query)
        res = res.fetchone()
        print(res)

        fio_in_mass = fio.split(' ')
        if len(fio_in_mass) == 3:
            if res == None:
                print(fio, username, password,secret_key,max_id)
                query = f'''INSERT INTO users (fio, nick, password, secret_key, teacher, id) VALUES ('{fio}', '{username}', '{password}', '{secret_key}', 'no', {max_id});'''
                cur.execute(query)
                con.commit()
                con.close()
                resp = make_response(redirect('hello', 301))
                resp.set_cookie(username, secret_key, 60*60*24*15)
                return resp
            else:
                error = "Выбранный вами Username уже занят"
                return render_template('registration.html', error=error)
        else:
                error = "ФИО должно состоять из 3 слов"
                return render_template('registration.html', error=error)

    elif request.method == "POST":
        error = 'Invalid username/password'

    
    return render_template('registration.html', error=error)

@app.route("/hello")
def hello():
    reqinnone = 0
    con = sqlite3.connect('app.db')
    cur = con.cursor()
    res = cur.execute('''SELECT nick FROM users;''')
    res = res.fetchall()
    for i in res:
        query = f'''SELECT password FROM users WHERE nick='{i[0]}';'''
        passwd = cur.execute(query)
        passwd = passwd.fetchall()
        passwd = passwd[0]
        secret_key = bs64.b64encode(str.encode(i[0]+passwd[0][:2])).decode("utf-8") 
        ##print('"'+str(request.cookies.get(i[0]))+'"','"'+secret_key+'"')
        if request.cookies.get(i[0]) == secret_key:

            query = f'''SELECT fio FROM users WHERE nick='{i[0]}';'''
            fio = cur.execute(query)
            fio = fio.fetchall()
            fio = fio[0][0].split(' ')
            print(fio)
            letters = fio[0][:1]+fio[1][:1]
            print(letters)

            return render_template('hello.html', username=i[0], letters=letters)
        elif request.cookies.get(i[0]) != None:
            res = make_response(redirect('hello', 301))
            res.set_cookie(i[0], request.cookies.get(i[0]), max_age=0)
            return res
        elif request.cookies.get(i[0]) == None:
            reqinnone == None
    if reqinnone == None:
        return redirect('/login', 301)
    return redirect('/login', 301)

@app.route("/about")
def about():
    return render_template("about.html")

if __name__ == "__main__":
    app.run("0.0.0.0")
#    app.run()
