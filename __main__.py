from pydoc import stripid
import flask
import db
import json

app = flask.Flask(__name__)
app.config.from_file('config.json', load=json.load)

@app.route('/api/create_form', methods=['POST'])
def create_form():
    data = flask.request.json
    if data == None:
        return '{"successful": false, "error": "Notika kļūda!", "id": null}'
    id = db.create_form(data['name'], data['password'], data['questions'])
    if id == False:
        return '{"successful": false, "error": "Notika kļūda!", "id": null}'
    return '{"successful": true, "error": null, "id": "'+id+'"}'

@app.route('/api/edit_form', methods=['POST'])
def edit_form():
    data = flask.request.json
    if data == None:
        return '{"successful": false, "error": "Notika kļūda!"}'

    if 'id' not in flask.session or flask.session['id'] != data['id']:
        return '{"successful": false, "error": "Notika kļūda!"}'

    if db.modify_form(data['id'], data['name'], data['questions']):
        return '{"successful": true, "error": null}'
    else:
        return '{"successful": false, "error": "Notika kļūda!"}'

@app.route('/api/login', methods=['POST'])
def login():
    data = flask.request.json
    if data == None:
        return flask.redirect(flask.url_for('home'))

    if db.verify_form_password(data['id'], data['password']):
        flask.session['id'] = data['id']
        return '{"successful": true}'
    else:
        return '{"successful": false}'

@app.route('/api/logout', methods=['POST'])
def logout():
    flask.session.pop('id', None)
    return '{"successful": true}'

@app.route('/api/fill_form', methods=['POST'])
def fill_form():
    data = flask.request.json
    if data == None:
        return '{"successful": false, "error": "Notika kļūda!"}'

    # Jāpārbauda iegūtie dati
    if not data["id"]:
        return '{"successful": false, "error": "Notika kļūda!"}'

    questions = db.get_form_questions(data["id"])
    if not questions:
        return '{"successful": false, "error": "Notika kļūda!"}'

    for q in questions:
        if not data["answers"].get(q["id"]).strip() and q["required"]:
            return '{"successful": false, "error": "Jāaizpilda visi obligātie jautājumi!"}'

    # Atbilde jāsaglabā datubāzē
    if db.register_answer(data['id'], data['answers']):
        flask.session['done'] = 'true' # Ļoti īslaicīga sīkdatne, lai parādītu "paldies par aizpildīšanu" lapu
        return '{"successful": true, "error": null}'
    else:
        return '{"successful": false, "error": "Notika kļūda!"}'

@app.route('/')
def home():
    return flask.render_template('new_form.html')

@app.route('/<id>')
def form(id):
    if db.form_exists(id):
        if 'id' in flask.session and flask.session['id'] == id:
            return flask.render_template('edit_form.html', id=id, name=db.get_form_name(id), questions=db.get_form_questions(id))
        elif 'done' in flask.session:
            flask.session.pop('done', None)
            return flask.render_template('thank_you.html', name=db.get_form_name(id))
        else:
            return flask.render_template('fill_form.html', id=id, name=db.get_form_name(id), questions=db.get_form_questions(id))
    else:
        return flask.redirect(flask.url_for('home'))

app.run(debug=True)
