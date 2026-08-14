import os

from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@app.route('/admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/student')
def student_dashboard():
    return render_template('student_dashboard.html')

@app.route('/verifier')
def verifier_dashboard():
    return render_template('verifier_dashboard.html')

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', '0') == '1')