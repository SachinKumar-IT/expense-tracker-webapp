from flask import Flask, redirect, url_for, flash, request, send_file, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime
import pandas as pd
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sachin_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expense_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    expenses = db.relationship('Expense', backref='author', lazy=True)
    budget = db.relationship('Budget', backref='user', uselist=False)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    monthly_limit = db.Column(db.Float, nullable=False, default=0.0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Currency Configuration
INR_TO_USD_RATE = 83.0

def convert_inr_to_usd(amount_in_inr):
    return amount_in_inr / INR_TO_USD_RATE

@app.context_processor
def utility_processor():
    def format_currency(amount):
        pref = session.get('currency_pref', 'BOTH')
        inr = f"₹{amount:,.2f}"
        usd = f"${convert_inr_to_usd(amount):,.2f}"
        
        if pref == 'INR':
            return inr
        elif pref == 'USD':
            return usd
        else:
            return f"{inr} ({usd})"
            
    return dict(format_currency=format_currency, current_currency_pref=session.get('currency_pref', 'BOTH'))

def render_page(template_name, **context):
    import flask
    return flask.render_template(template_name, **context)

@app.route('/set_currency/<pref>')
def set_currency(pref):
    if pref in ['INR', 'USD', 'BOTH']:
        session['currency_pref'] = pref
        flash(f'Currency display updated to {pref}', 'info')
    return redirect(request.referrer or url_for('dashboard'))

# Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('register'))
            
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        # Initialize budget for the new user
        budget = Budget(monthly_limit=0.0, user_id=user.id)
        db.session.add(budget)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    response = render_page('register.html')
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    response = render_page('login.html')
    return response

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    response = render_page('index.html')
    return response

@app.route('/dashboard')
@login_required
def dashboard():
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
    budget = Budget.query.filter_by(user_id=current_user.id).first()
    
    total_expenses = sum(expense.amount for expense in expenses)
    monthly_limit = budget.monthly_limit if budget else 0.0
    
    # Calculate categories for chart
    categories = {}
    for expense in expenses:
        if expense.category in categories:
            categories[expense.category] += expense.amount
        else:
            categories[expense.category] = expense.amount
            
    response = render_page('dashboard.html', expenses=expenses, total_expenses=total_expenses, 
                               monthly_limit=monthly_limit, categories=categories)
    return response

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        title = request.form.get('title')
        amount = float(request.form.get('amount'))
        category = request.form.get('category')
        date_str = request.form.get('date')
        date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.utcnow().date()
        
        expense = Expense(title=title, amount=amount, category=category, date=date, author=current_user)
        db.session.add(expense)
        db.session.commit()
        flash('Expense added successfully!', 'success')
        return redirect(url_for('dashboard'))
    response = render_page('add_expense.html')
    return response

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_expense(id):
    expense = db.get_or_404(Expense, id)
    if expense.author != current_user:
        flash('You are not authorized to edit this expense', 'danger')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        expense.title = request.form.get('title')
        expense.amount = float(request.form.get('amount'))
        expense.category = request.form.get('category')
        date_str = request.form.get('date')
        if date_str:
            expense.date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        db.session.commit()
        flash('Expense updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    response = render_page('edit_expense.html', expense=expense)
    return response

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_expense(id):
    expense = db.get_or_404(Expense, id)
    if expense.author != current_user:
        flash('You are not authorized to delete this expense', 'danger')
        return redirect(url_for('dashboard'))
    db.session.delete(expense)
    db.session.commit()
    flash('Expense deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/budget', methods=['POST'])
@login_required
def update_budget():
    budget = Budget.query.filter_by(user_id=current_user.id).first()
    if not budget:
        budget = Budget(user_id=current_user.id)
        db.session.add(budget)
    try:
        budget.monthly_limit = float(request.form.get('monthly_limit'))
        db.session.commit()
        flash('Budget updated successfully!', 'success')
    except ValueError:
        flash('Invalid budget amount.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/export')
@login_required
def export_csv():
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    data = [{
        'Title': e.title,
        'Amount': e.amount,
        'Category': e.category,
        'Date': e.date.strftime('%Y-%m-%d')
    } for e in expenses]
    
    df = pd.DataFrame(data)
    
    # Ensure static directory exists
    static_dir = os.path.join(app.root_path, 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
        
    csv_path = os.path.join(static_dir, 'expenses.csv')
    df.to_csv(csv_path, index=False)
    return send_file(csv_path, as_attachment=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
