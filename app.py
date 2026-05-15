from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO
import sqlite3

app = Flask(__name__)
socketio = SocketIO(app)

DB_NAME = 'database.db'


# =========================
# DATABASE INITIALIZATION
# =========================

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Products Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL
        )
    ''')

    # Audit Log Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            action TEXT,
            old_quantity INTEGER,
            new_quantity INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


init_db()


# =========================
# HOME PAGE
# =========================

@app.route('/')
def index():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT * FROM products")
    products = c.fetchall()

    conn.close()

    return render_template('index.html', products=products)


# =========================
# ADD PRODUCT
# =========================

@app.route('/add', methods=['GET', 'POST'])
def add_product():

    if request.method == 'POST':

        name = request.form['name']
        category = request.form['category']
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute("""
            INSERT INTO products (name, category, quantity, price)
            VALUES (?, ?, ?, ?)
        """, (name, category, quantity, price))

        product_id = c.lastrowid

        # Audit log
        c.execute("""
            INSERT INTO audit_log
            (product_id, action, old_quantity, new_quantity)
            VALUES (?, ?, ?, ?)
        """, (product_id, 'ADD', 0, quantity))

        conn.commit()
        conn.close()

        # Real-time update
        socketio.emit('stock_update', {
            'message': f'Product "{name}" added'
        })

        return redirect(url_for('index'))

    return render_template('add_product.html')


# =========================
# EDIT PRODUCT
# =========================

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_product(id):

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    if request.method == 'POST':

        name = request.form['name']
        category = request.form['category']
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])

        # Get old quantity
        c.execute("SELECT quantity FROM products WHERE id=?", (id,))
        old_quantity = c.fetchone()[0]

        # Update product
        c.execute("""
            UPDATE products
            SET name=?, category=?, quantity=?, price=?
            WHERE id=?
        """, (name, category, quantity, price, id))

        # Audit log
        c.execute("""
            INSERT INTO audit_log
            (product_id, action, old_quantity, new_quantity)
            VALUES (?, ?, ?, ?)
        """, (id, 'UPDATE', old_quantity, quantity))

        conn.commit()
        conn.close()

        # Real-time update
        socketio.emit('stock_update', {
            'message': f'Product "{name}" updated'
        })

        return redirect(url_for('index'))

    # GET request
    c.execute("SELECT * FROM products WHERE id=?", (id,))
    product = c.fetchone()

    conn.close()

    return render_template('edit_product.html', product=product)


# =========================
# DELETE PRODUCT
# =========================

@app.route('/delete/<int:id>')
def delete_product(id):

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Get old product info
    c.execute("SELECT name, quantity FROM products WHERE id=?", (id,))
    product = c.fetchone()

    if product:
        product_name = product[0]
        old_quantity = product[1]

        # Audit log
        c.execute("""
            INSERT INTO audit_log
            (product_id, action, old_quantity, new_quantity)
            VALUES (?, ?, ?, ?)
        """, (id, 'DELETE', old_quantity, 0))

        # Delete product
        c.execute("DELETE FROM products WHERE id=?", (id,))

        conn.commit()

        # Real-time update
        socketio.emit('stock_update', {
            'message': f'Product "{product_name}" deleted'
        })

    conn.close()

    return redirect(url_for('index'))


# =========================
# PRODUCT HISTORY
# =========================

@app.route('/history/<int:id>')
def history(id):

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT action, old_quantity, new_quantity, timestamp
        FROM audit_log
        WHERE product_id=?
        ORDER BY timestamp DESC
    """, (id,))

    logs = c.fetchall()

    conn.close()

    return render_template('history.html', logs=logs)


# =========================
# DASHBOARD
# =========================

@app.route('/dashboard')
def dashboard():

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Product stock data
    c.execute("SELECT name, quantity FROM products")
    products = c.fetchall()

    # Revenue by category
    c.execute("""
        SELECT category, SUM(price * quantity)
        FROM products
        GROUP BY category
    """)
    revenue = c.fetchall()

    conn.close()

    return render_template(
        'dashboard.html',
        products=products,
        revenue=revenue
    )


# =========================
# CONTACT PAGE
# =========================

# @app.route('/contact')
# def contact():
#     return render_template('contact.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        print(name, email, message)  # later you can store in DB

        return redirect(url_for('contact'))

    return render_template('contact.html')


# =========================
# MAIN
# =========================

if __name__ == '__main__':
    socketio.run(app, debug=True)