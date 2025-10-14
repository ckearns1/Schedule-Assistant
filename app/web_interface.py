from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure key in production

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/set_role/<role>')
def set_role(role):
    session['role'] = role
    return redirect(url_for('availability_form'))

@app.route('/availability')
def availability_form():
    role = session.get('role', 'guest')
    return render_template('availability_form.html', role=role)

@app.route('/submit_availability', methods=['POST'])
def submit_availability():
    return render_template('submit_availability.html')

@app.route('/classes')
def classes():
    return render_template('classes.html')

if __name__ == '__main__':
    app.run(debug=True)