from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from predictor import predict_price, get_stock_analysis, calculate_risk_assessment, calculate_confidence_score
import yfinance as yf
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # change this in production

# SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Load user
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Available tickers
TICKERS = [f.replace('.h5', '') for f in os.listdir('models') if f.endswith('.h5')]

@app.route('/')
@login_required
def home():
    return render_template('index.html', tickers=TICKERS, username=current_user.username)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('register'))
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    ticker = request.form['ticker']
    try:
        df = yf.download(ticker, period='1y')
        if len(df) < 60:
            raise ValueError("Not enough historical data (need ≥60 days)")
        prediction = predict_price(ticker, df)
        analysis = get_stock_analysis(ticker, df, prediction['accuracy_calc'])
        analysis['confidence_score'] = calculate_confidence_score(analysis['reasons'], analysis)
        analysis['risk_score'] = calculate_risk_assessment(analysis)
        analysis['accuracy'] = prediction['accuracy_calc']
        prediction = prediction['predicted']
        return render_template('results.html', ticker=ticker, prediction=prediction, analysis=analysis)
    except Exception as e:
        return render_template('index.html', tickers=TICKERS, error=str(e))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Now runs inside the app context
    app.run(host='0.0.0.0', port=5000, debug=True)
