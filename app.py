from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from database import get_db, init_db
from datetime import date, timedelta
import resend
import bcrypt
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import os
app = Flask(__name__, 
    static_folder=os.path.join(os.path.dirname(__file__), 'frontend'),
    static_url_path='')
CORS(app)
init_db()

EMAIL = os.environ.get('EMAIL', 'sarathiilangovan@gmail.com')
PASSWORD = os.environ.get('PASSWORD', 'utpu ldtu mksj xglh')
def send_email_alert(product_name, expiry_date, quantity, to_email):
    try:
        resend.api_key = os.environ.get('RESEND_API_KEY', '')
        resend.Emails.send({
            "from": "StockTracker <onboarding@resend.dev>",
            "to": to_email,
            "subject": f"⚠️ StockTracker Alert: {product_name} Expiring Soon!",
            "html": f"""
            <h2>⚠️ Expiry Alert - StockTracker</h2>
            <p><b>Product:</b> {product_name}</p>
            <p><b>Quantity:</b> {quantity}</p>
            <p><b>Expiry:</b> {expiry_date}</p>
            <p>Please take action before the product expires!</p>
            <p>- StockTracker System</p>
            """
        })
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

@app.route('/')
def index():
    return send_from_directory('frontend', 'index.html')

@app.route('/api/products', methods=['GET'])
def get_products():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products ORDER BY expiry_date ASC")
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(products)

@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (name, category, quantity, expiry_date) VALUES (?, ?, ?, ?)",
        (data['name'], data['category'], data['quantity'], data['expiry_date'])
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "✅ Product added!"})

@app.route('/api/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "✅ Deleted!"})

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    conn = get_db()
    cursor = conn.cursor()
    today = date.today().isoformat()
    alert_date = (date.today() + timedelta(days=7)).isoformat()
    cursor.execute(
        "SELECT * FROM products WHERE expiry_date BETWEEN ? AND ?",
        (today, alert_date)
    )
    alerts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(alerts)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM products")
    total = cursor.fetchone()['total']
    today = date.today().isoformat()
    alert_date = (date.today() + timedelta(days=7)).isoformat()
    cursor.execute(
        "SELECT COUNT(*) as expiring FROM products WHERE expiry_date BETWEEN ? AND ?",
        (today, alert_date)
    )
    expiring = cursor.fetchone()['expiring']
    cursor.execute("SELECT SUM(quantity) as stock FROM products")
    stock = cursor.fetchone()['stock'] or 0
    conn.close()
    return jsonify({
        "total_products": total,
        "expiring_soon": expiring,
        "total_stock": stock
    })

@app.route('/api/send-alerts', methods=['POST'])
def send_alerts():
    data = request.json
    to_email = data.get('email')
    if not to_email:
        return jsonify({"message": "❌ Email required!"})
    conn = get_db()
    cursor = conn.cursor()
    today = date.today().isoformat()
    alert_date = (date.today() + timedelta(days=7)).isoformat()
    cursor.execute(
        "SELECT * FROM products WHERE expiry_date BETWEEN ? AND ?",
        (today, alert_date)
    )
    expiring = [dict(row) for row in cursor.fetchall()]
    conn.close()
    if not expiring:
        return jsonify({"message": "✅ No expiring products!"})
    for product in expiring:
        send_email_alert(product['name'], product['expiry_date'], product['quantity'], to_email)
    return jsonify({"message": f"✅ Alert sent for {len(expiring)} products!"})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    hashed = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (data['name'], data['email'], hashed)
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "✅ Registration successful!"})
    except:
        conn.close()
        return jsonify({"message": "❌ Email already exists!"})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email=?", (data['email'],))
    user = cursor.fetchone()
    conn.close()
    if user and bcrypt.checkpw(data['password'].encode('utf-8'), user['password']):
        return jsonify({"message": "✅ Login successful!", "name": user['name'], "role": user['role'], "email": user['email']})
    return jsonify({"message": "❌ Invalid email or password!"})

@app.route('/login')
def login_page():
    return send_from_directory('frontend', 'login.html')

@app.route('/chart.js')
def serve_chart():
    return send_from_directory('frontend', 'chart.js')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)