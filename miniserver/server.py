# server.py

import pickle
import io
from flask import Flask, request, jsonify
from werkzeug.exceptions import BadRequest
from utils.sqlite import ReportDatabase, sqlite3
from utils.nxmanager import ErrorChecker
import os
import uuid
import datetime
from flask import Flask, g
from flask_cors import CORS  # Import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize the ReportDatabase and ErrorChecker
DATABASE_PATH = './data_samples/sqlite_db/test_reports.db'
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        db.row_factory = sqlite3.Row
    return db

@app.route('/initialize_db', methods=['POST'])
def initialize_db():
    db = get_db()  # Only call get_db() inside a route
    # Perform initialization operations here
    return "Database initialized"


with app.app_context():
    db = get_db()  # Initialize the database here if needed

report_db = ReportDatabase(db)
error_checker = ErrorChecker()

# Route for submitting a report
@app.route('/submit_report', methods=['POST'])
def submit_report():
    """Endpoint to submit a report with team, NIU, and pickle file of graphs"""
    try:
        # Fetch team name, NIU, and file from the form data
        team_name = request.form.get('team_name')
        niu = request.form.get('niu')
        file = request.files.get('file')

        if not all([team_name, niu, file]):
            return jsonify({'error': 'team_name, niu, and file are required'}), 400

        # Deserialize the uploaded pickle file
        try:
            graph_data = pickle.load(file.stream)
        except (pickle.UnpicklingError, io.UnsupportedOperation) as e:
            return jsonify({'error': 'Invalid pickle file provided'}), 400

        # Verify and calculate errors using ErrorChecker
        try:
            single_day_error, five_days_error, ten_days_error = error_checker(graph_data)
        except PermissionError as e:
            return jsonify({'error': str(e)}), 400

        # Insert user and team into the database if not already existing
        report_db.add_user(niu)
        report_db.add_team(team_name, niu)

        # Insert report with the calculated errors
        report_db.add_report(
            id_report=str(uuid.uuid4()),  # Auto-incrementing id
            team_name=team_name,
            reported_at=str(datetime.datetime.now()),  # You can customize this for actual timestamp
            reported_from='API',
            total_error=0.3 * (single_day_error + five_days_error * 0.2 + ten_days_error * 0.09),
            single_day_error=single_day_error,
            five_days_error=five_days_error,
            ten_days_error=ten_days_error
        )

        return jsonify({'message': 'Report submitted successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Route for loading ranking
@app.route('/load_ranking', methods=['GET'])
def load_ranking():
    """Endpoint to load report rankings sorted by single_day_error, including NIU for each report"""
    # Fetch and sort reports by single_day_error
    reports = report_db.get_all_reports()
    sorted_reports = sorted(reports, key=lambda x: x['total_error'])

    # Prepare ranking response with team_name, single_day_error, and NIU
    ranking = [
        {
            'team_name': report['team_name'],
            'single_day_error': report['single_day_error'],
            'five_days_error': report['five_days_error'],
            'ten_days_error': report['ten_days_error'],
            'niu': report['NIU'],
            'total_error': report['total_error']
        }
        for report in sorted_reports
    ]

    print(ranking)
    return jsonify(ranking), 200

# Cleanup on shutdown

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
