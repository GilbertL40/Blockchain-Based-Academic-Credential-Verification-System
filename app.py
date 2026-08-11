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

if __name__ == '__main__':
    app.run(debug=True)