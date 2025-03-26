import sqlite3
import json, random, string
import bcrypt

db = sqlite3.connect('database.db', check_same_thread=False)
c = db.cursor()

"""
Dažādas funkcijas darbībām ar datubāzi
"""

def create_form(name, password, questions):
    data = json.dumps(questions)
    id = ''.join(random.choice(string.digits + string.ascii_letters) for i in range(10))
    hashed_pwd = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    try:
        c.execute("""INSERT INTO forms (id, password, name, questions) VALUES (?, ?, ?, ?);""", (id, hashed_pwd, name, data))
        db.commit()
    except:
        return False

    return id

def modify_form(id, name, questions):
    try:
        data = json.dumps(questions)
        c.execute("""UPDATE forms SET name = ?, questions = ? WHERE id = ?;""", (name, data, id))
        db.commit()
    except:
        return False

    return True

def form_exists(id):
    try:
        result = c.execute("""SELECT * FROM forms WHERE id=?;""", [id])
    except:
        return False

    return result.fetchone() is not None

def get_form_name(id):
    try:
        result = c.execute("""SELECT name FROM forms WHERE id=?;""", [id])
    except:
        return False

    form = result.fetchone()
    if form == None:
        return False
    return form[0]

def get_form_questions(id):
    try:
        result = c.execute("""SELECT questions FROM forms WHERE id=?;""", [id])
        db_data = result.fetchone()
        if db_data == None:
            return False
        json_data = json.loads(db_data[0])
    except:
        return False

    return json_data

def verify_form_password(id, password):
    try:
        result = c.execute("""SELECT password FROM forms WHERE id=?;""", [id])
        return bcrypt.checkpw(password.encode("utf-8"), result.fetchone()[0])
    except:
        return False

def register_answer(form_id, answers):
    id = random.randrange(1000000000, 9999999999)
    try:
        data = json.dumps(answers)
        c.execute("""INSERT INTO answers (id, form_id, data) VALUES (?, ?, ?);""", (id, form_id, data))
        db.commit()
    except:
        return False
    return True

def get_form_answers(id):
    try:
        result = c.execute("""SELECT data FROM answers WHERE form_id=?;""", [id])
        return [json.loads(i[0]) for i in result.fetchall()]
    except:
        return False

def remove_form_answers(id):
    try:
        c.execute("""DELETE FROM answers WHERE form_id=?;""", [id])
        return True
    except:
        return False

"""
Ja neeksistē, jāizveido tabulas
"""

c.execute("""CREATE TABLE IF NOT EXISTS "forms" (
	"id"	TEXT NOT NULL UNIQUE,
	"password"	TEXT,
	"name"	TEXT,
	"questions"	TEXT,
	PRIMARY KEY("id")
);""")
c.execute("""CREATE TABLE IF NOT EXISTS "answers" (
	"id"	INTEGER NOT NULL UNIQUE,
	"form_id"	TEXT,
	"data"	TEXT,
	PRIMARY KEY("id"),
	FOREIGN KEY("form_id") REFERENCES forms(id)
);""")
