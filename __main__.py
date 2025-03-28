import flask
import db
import io
import base64
import json
import matplotlib.pyplot as plt
import matplotlib
import pandas as pd

matplotlib.use('Agg')

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

    # Pārbauda, vai obligātie jautājumi ir aizpildīti
    for q in questions:
        if q.get("id") == None:
            return '{"successful": false, "error": "Notika kļūda!"}'
        if q["required"]:
            if q["type"] == "text":
                continue
            invalid_response = '{"successful": false, "error": "Jāaizpilda visi obligātie jautājumi!"}'
            if q["id"] not in data["answers"]:
                return invalid_response
            if q["type"] != "checkbox":
                if not data["answers"][q["id"]].strip():
                    return invalid_response

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

@app.route('/api/get_form_answers/<id>', methods=['GET'])
def form_answers(id):
    if 'id' not in flask.session or flask.session['id'] != id:
        return '{"successful": false}'

    answers = db.get_form_answers(id)  # Get answers from the database
    questions = db.get_form_questions(id)

    if answers == False:
        return '{"successful": false}'

    if not questions:
        return '{"successful": false}'

    # Using Pandas because we have to
    df_answers = pd.DataFrame(answers)
    df_questions = pd.DataFrame(questions)

    text_data = {} # Store text answers for free text field questions

    # Prepare data for Pie charts (based on multiple_choice)
    pie_data = {}  # Store pie charts per multiple-choice question

    # Prepare data for Histograms (based on checkbox)
    hist_data = {}  # Store histograms per checkbox question

    # Mapping question IDs to their types (e.g., 'multiple_choice', 'checkbox')
    question_types = df_questions.set_index('id')['type'].to_dict()

    # Mapping question IDs to the actual question text
    question_texts = df_questions.set_index('id')['text'].to_dict()

    # Loop through answers and create separate charts for each question type
    for question_id, answer_type in question_types.items():
        if not str(question_id) in df_answers: # Avoid errors when no answers are in
            continue

        if answer_type == 'multiple_choice':  # For multiple_choice questions
            counts = df_answers[str(question_id)].dropna().value_counts().to_dict()
            pie_data[question_id] = counts

        elif answer_type == 'checkbox':  # For checkbox questions
            exploded = df_answers[str(question_id)].explode().dropna()
            counts = exploded.value_counts().to_dict()
            hist_data[question_id] = counts

        elif answer_type in ['short_text', 'long_text']: # For text questions
            responses = df_answers[str(question_id)].dropna().tolist()
            text_data[question_id] = {"question": question_texts[question_id], "responses": responses}

    # Generate Pie charts for multiple_choice questions
    pie_charts = {}
    for question_id, answer_counts in pie_data.items():
        question_text = question_texts.get(question_id, f"Question {question_id}")

        fig, ax = plt.subplots(figsize=(8, 6))
        ax.pie(answer_counts.values(), labels=answer_counts.keys(), autopct='%1.1f%%', startangle=90)
        ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
        ax.set_title(f"{question_text}")

        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        pie_charts[question_id] = base64.b64encode(img.getvalue()).decode('utf-8')

    # Generate Histograms for checkbox questions
    histograms = {}
    for question_id, checkbox_answers in hist_data.items():
        question_text = question_texts.get(question_id, f"Question {question_id}")
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.bar(checkbox_answers.keys(), checkbox_answers.values())
        ax.set_title(f"{question_text}")
        ax.set_ylabel('Number of Responses')

        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        histograms[question_id] = base64.b64encode(img.getvalue()).decode('utf-8')

    # Return the pie charts and histograms as base64 images
    return json.dumps({
        "successful": True,
        "text_answers": text_data,
        "pie_charts": pie_charts,  # Each pie chart for a multiple-choice question
        "histograms": histograms  # Each histogram for a checkbox question
    })

@app.route('/api/download_csv/<id>', methods=['GET'])
def download_csv(id):
    if 'id' not in flask.session or flask.session['id'] != id:
        return '{"successful": false}'

    answers = db.get_form_answers(id)
    questions = db.get_form_questions(id)
    if not answers or not questions:
        return '{"successful": false}'

    # Use Pandas to create a CSV file
    df_answers = pd.DataFrame(answers)

    csv = io.StringIO()
    df_answers.to_csv(csv, index=False)
    csv.seek(0)

    # Create response with CSV file
    return flask.send_file(
        io.BytesIO(csv.getvalue().encode('utf-8')),
        as_attachment=True,
        download_name=f'{id}.csv'
    )

@app.route('/api/upload_csv/<id>', methods=['POST'])
def upload_csv(id):
    if 'id' not in flask.session or flask.session['id'] != id:
        return '{"successful": false, "error": "Notika kļūda!"}'

    if 'file' not in flask.request.files:
        return '{"successful": false}'

    file = flask.request.files['file']
    df = pd.read_csv(file)

    answers = df.to_dict(orient='records')

    # Convert strings to objects
    for i in answers:
        for o in i.keys():
            if isinstance(i[o], str) and i[o].strip().startswith("["):
                i[o] = json.loads(i[o].replace("'", '"'))

    # Upload everything to DB
    db.remove_form_answers(id)
    for i in answers:
        db.register_answer(id, i)

    return '{"successful": true}'

app.run(debug=True)
