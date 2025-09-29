from flask import Flask, render_template, request, redirect, url_for, send_file, session, flash
import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns
import uuid
import io
import matplotlib
matplotlib.use('Agg')  # ✅ MUST be before importing pyplot
import matplotlib.pyplot as plt
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
# Import authentication helpers
from auth import register_user, validate_login

# dataabase connection


# MySQL DB config
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'student',
    'database': 'data_dashboard'
}

def init_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(250) UNIQUE,
            password_hash VARCHAR(100)
        )
    ''')
    conn.commit()
    conn.close()

def register_user(email, password):
    conn = None  # ensure conn is defined
    hashed_password = generate_password_hash(password)
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Users (email, password_hash) VALUES (%s, %s)", (email, hashed_password))
        conn.commit()
        return True
    except mysql.connector.IntegrityError:
        return False
    finally:
        if conn:
            conn.close()


def validate_login(email, password):
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM Users WHERE email = %s", (email,))
        result = cursor.fetchone()
        return check_password_hash(result[0], password) if result else False
    finally:
        if conn:
            conn.close()


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'your_secret_key_here'  # Required for session handling

data_store = {}

# Home (login required)
@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

# User Registration
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if register_user(email, password):
            flash("✅ Registration successful. Please login.")
            return redirect(url_for('login'))
        else:
            flash("⚠️ User already exists.")
    return render_template('signup.html')


# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if validate_login(email, password):
            session['user'] = email
            flash("✅ Login successful.")
            return redirect(url_for('index'))
        else:
            flash("❌ Invalid credentials.")
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("You have been logged out.")
    return redirect(url_for('login'))

# Upload file
@app.route('/upload', methods=['POST'])
def upload():
    if 'user' not in session:
        return redirect(url_for('login'))

    file = request.files['file']
    if file:
        filename = str(uuid.uuid4()) + "_" + file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        df = pd.read_csv(filepath) if filename.endswith('.csv') else pd.read_excel(filepath)
        data_store['df'] = df
        return redirect(url_for('dashboard'))

    flash("No file uploaded.")
    return redirect(url_for('index'))

# Dashboard
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    df = data_store.get('df')
    if df is None:
        flash("⚠️ Please upload a dataset first.")
        return redirect(url_for('index'))

    if request.method == 'POST':
        action = request.form.get('action')
        column = request.form.get('column')
        if action == 'dropna':
            df.dropna(inplace=True)
        elif action == 'fillna_mean' and column in df.columns:
            df[column].fillna(df[column].mean(), inplace=True)
        elif action == 'fillna_median' and column in df.columns:
            df[column].fillna(df[column].median(), inplace=True)
        data_store['df'] = df

    desc = df.describe(include='all').to_html(classes='table table-striped')
    return render_template('dashboard.html', tables=desc, columns=df.columns)

@app.route('/visualize', methods=['POST'])
def visualize():
    if 'user' not in session:
        return redirect(url_for('login'))

    df = data_store.get('df')
    chart_type = request.form.get('chart_type')
    x_axis = request.form.get('x_axis')
    y_axis = request.form.get('y_axis')

    plt.clf()  # Clear the current figure

    try:
        # Plot based on chart type
        if chart_type == 'bar':
            df[x_axis].value_counts().plot(kind='bar')
        elif chart_type == 'scatter':
            df.plot.scatter(x=x_axis, y=y_axis)
        elif chart_type == 'heatmap':
            sns.heatmap(df.corr(), annot=True)
        elif chart_type == 'histogram':
            df.hist(figsize=(10, 6))
        elif chart_type == 'pie':
            df.iloc[:, -1].value_counts().plot.pie(autopct='%1.1f%%')

        # Save the figure instead of showing it
        chart_path = 'static/chart.png'
        plt.tight_layout()
        plt.savefig(chart_path)
        plt.close('all')  # ✅ Important: close plot to avoid memory issues

        flash("✅ Chart generated successfully!", "success")

    except Exception as e:
        flash(f"⚠️ Visualization error: {e}", "danger")
        plt.close('all')

    return redirect(url_for('dashboard'))


# Export cleaned data
@app.route('/export/<filetype>')
def export(filetype):
    if 'user' not in session:
        return redirect(url_for('login'))

    df = data_store.get('df')
    output = io.BytesIO()

    if filetype == 'csv':
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(output, download_name="cleaned_data.csv", as_attachment=True, mimetype='text/csv')
    elif filetype == 'excel':
        df.to_excel(output, index=False)
        output.seek(0)
        return send_file(output, download_name="cleaned_data.xlsx", as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    return "Unsupported export type"

# Run app
if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    app.run(debug=True)
