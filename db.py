import sqlite3
import json, random, string

db = sqlite3.connect("database.db", check_same_thread=False)
c = db.cursor()

### Ja neeksistē, jāizveido tabulas ###
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

### Dažādas funkcijas darbībām ar datubāzi ###
def create_form(name, password, questions):
    data = json.dumps(questions)
    id = ''.join(random.choice(string.digits + string.ascii_letters) for i in range(10))
    c.execute("""INSERT INTO forms (id, password, name, questions) VALUES (?, ?, ?, ?);""", (id, password, name, data))
    db.commit()
    return id

def modify_form(id, name, questions):
    data = json.dumps(questions)
    c.execute("""UPDATE forms SET name = ?, questions = ? WHERE id = ?;""", (name, data, id))
    db.commit()
    return True

def form_exists(id):
    result = c.execute("""SELECT * FROM forms WHERE id=?;""", [id])
    return result.fetchone() is not None

def get_form_name(id):
    result = c.execute("""SELECT name FROM forms WHERE id=?;""", [id])
    return result.fetchone()[0]

def get_form_questions(id):
    result = c.execute("""SELECT questions FROM forms WHERE id=?;""", [id])
    return json.loads(result.fetchone()[0])

def verify_form_password(id, pwd): # TEMPORARY SOLUTION, MUST SWITCH TO BCRYPT
    result = c.execute("""SELECT password FROM forms WHERE id=?;""", [id])

    return pwd == result.fetchone()[0]

def register_answer(form_id, answers):
    data = json.dumps(answers)
    id = random.randrange(1000000000, 9999999999)
    c.execute("""INSERT INTO answers (id, form_id, data) VALUES (?, ?, ?);""", (id, form_id, data))
    db.commit()
