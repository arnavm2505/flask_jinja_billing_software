from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import uuid
from datetime import datetime
import random
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bills (
            bill_number TEXT PRIMARY KEY,
            total REAL NOT NULL,
            products TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()
    conn.close()
    return render_template('index.html', products=products)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return "Invalid credentials", 401
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Username already exists"
        conn.close()
        return redirect(url_for('login'))
    return render_template('create_account.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET password = ? WHERE username = ?', (new_password, username))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        quantity = int(request.form['quantity'])
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO products (name, price, quantity) VALUES (?, ?, ?)', (name, price, quantity))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('add_product.html')

@app.route('/update/<int:product_id>', methods=['GET', 'POST'])
@login_required
def update_product(product_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    conn.close()
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        quantity = int(request.form['quantity'])
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE products SET name = ?, price = ?, quantity = ? WHERE id = ?', (name, price, quantity, product_id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('update_product.html', product=product)

@app.route('/delete/<int:product_id>', methods=['GET', 'POST'])
@login_required
def delete_product(product_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

def generate_bill_number():
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    random_number = random.randint(100, 999)
    return f"BILL-{timestamp}-{random_number}"

@app.route('/bill', methods=['GET', 'POST'])
@login_required
def generate_bill():
    if request.method == 'POST':
        product_ids = request.form.getlist('product_id')
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        products = []
        total = 0
        for product_id in product_ids:
            cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
            product = cursor.fetchone()
            products.append(product)
            total += product[2] * product[3]
        conn.close()
        bill_number = generate_bill_number()  # Generate a unique bill number
        
        # Store the bill in the database
        bill_products = [{'id': p[0], 'name': p[1], 'price': p[2], 'quantity': p[3], 'total': p[2]*p[3]} for p in products]
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO bills (bill_number, total, products) VALUES (?, ?, ?)', 
                       (bill_number, total, str(bill_products)))
        conn.commit()
        conn.close()
        
        return render_template('generate_bill.html', products=products, total=total, bill_number=bill_number)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()
    conn.close()
    return render_template('generate_bill.html', products=products)

@app.route('/search_bill', methods=['GET', 'POST'])
@login_required
def search_bill():
    bill = None
    if request.method == 'POST':
        bill_number = request.form['bill_number']
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM bills WHERE bill_number = ?', (bill_number,))
        bill_data = cursor.fetchone()
        conn.close()
        if bill_data:
            bill_products = eval(bill_data[2])  # Convert the stored string back to a list of dictionaries
            bill = {
                'bill_number': bill_data[0],
                'total': bill_data[1],
                'products': bill_products
            }
    return render_template('search_bill.html', bill=bill)

if __name__ == '__main__':
    app.run(debug=True)
