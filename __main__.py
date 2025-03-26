import flask
import db
import io
import base64
import json
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import pandas as pd
from matplotlib.ticker import MaxNLocator

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

@app.route('/api/get_form_answers/<id>', methods=['GET'])
def form_aswers(id):
    answers = db.get_form_answers(id)  # Get answers from the database
    questions = db.get_form_questions(id)
    
    if not answers:
        return '{"successful": false}'

    # Prepare data for Pie charts (based on multiple_choice)
    pie_data = {}  # Store pie charts per multiple-choice question

    # Prepare data for Histograms (based on checkbox)
    hist_data = {}  # Store histograms per checkbox question

    # Mapping question IDs to their types (e.g., 'multiple_choice', 'checkbox')
    question_types = {question['id']: question['type'] for question in questions}

    # Mapping question IDs to the actual question text
    question_texts = {question['id']: question['text'] for question in questions}

    # Loop through answers and create separate charts for each question type
    for answer_set in answers:
        for question_id, answer_type in question_types.items():
            if answer_type == 'multiple_choice':  # For multiple_choice questions
                pie_answer = answer_set.get(str(question_id))
                if pie_answer:
                    if question_id not in pie_data:
                        pie_data[question_id] = {}
                    if pie_answer not in pie_data[question_id]:
                        pie_data[question_id][pie_answer] = 0
                    pie_data[question_id][pie_answer] += 1

            elif answer_type == 'checkbox':  # For checkbox questions
                checkbox_answers = answer_set.get(str(question_id), [])
                for checkbox_answer in checkbox_answers:
                    if question_id not in hist_data:
                        hist_data[question_id] = {}
                    if checkbox_answer not in hist_data[question_id]:
                        hist_data[question_id][checkbox_answer] = 0
                    hist_data[question_id][checkbox_answer] += 1
    
    # Generate Pie charts for multiple_choice questions
    pie_charts = {}
    for question_id, answer_counts in pie_data.items():
        print(f"Generating Pie Chart for Question {question_id}")
        print(answer_counts)  # This prints the answer counts for each question_id
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
        "pie_charts": pie_charts,  # Each pie chart for a multiple-choice question
        "histograms": histograms  # Each histogram for a checkbox question
    })

    # answers = db.get_form_answers(id)
    # if answers == False:
    #     return json.dumps({"successful": False})
    # return json.dumps({"successful": True, "answers": answers})
app.run(debug=True)
