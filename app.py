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
            "to": [to_email],
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
    user_id = request.args.get('user_id')
    conn = get_db()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("SELECT * FROM products WHERE user_id=? ORDER BY expiry_date ASC", (user_id,))
    else:
        cursor.execute("SELECT * FROM products ORDER BY expiry_date ASC")
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(products)

@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.json
    user_id = data.get('user_id')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (name, category, quantity, expiry_date, user_id) VALUES (?, ?, ?, ?, ?)",
        (data['name'], data['category'], data['quantity'], data['expiry_date'], user_id)
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
    user_id = request.args.get('user_id')
    conn = get_db()
    cursor = conn.cursor()
    today = date.today().isoformat()
    alert_date = (date.today() + timedelta(days=7)).isoformat()
    if user_id:
        cursor.execute(
            "SELECT * FROM products WHERE expiry_date BETWEEN ? AND ? AND user_id=?",
            (today, alert_date, user_id)
        )
    else:
        cursor.execute(
            "SELECT * FROM products WHERE expiry_date BETWEEN ? AND ?",
            (today, alert_date)
        )
    
    alerts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(alerts)
@app.route('/api/stats', methods=['GET'])
def get_stats():
    user_id = request.args.get('user_id')
    conn = get_db()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("SELECT COUNT(*) as total FROM products WHERE user_id=?", (user_id,))
    else:
        cursor.execute("SELECT COUNT(*) as total FROM products")
    total = cursor.fetchone()['total']
    today = date.today().isoformat()
    alert_date = (date.today() + timedelta(days=7)).isoformat()
    if user_id:
        cursor.execute(
            "SELECT COUNT(*) as expiring FROM products WHERE expiry_date BETWEEN ? AND ? AND user_id=?",
            (today, alert_date, user_id)
        )
    else:
        cursor.execute(
            "SELECT COUNT(*) as expiring FROM products WHERE expiry_date BETWEEN ? AND ?",
            (today, alert_date)
        )
    expiring = cursor.fetchone()['expiring']
    if user_id:
        cursor.execute("SELECT SUM(quantity) as stock FROM products WHERE user_id=?", (user_id,))
    else:
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
      return jsonify({"message": "✅ Login successful!", "name": user['name'], "role": user['role'], "email": user['email'], "id": user['id']})
      return jsonify({"message": "❌ Invalid email or password!"})

@app.route('/login')
def login_page():
    return send_from_directory('frontend', 'login.html')

@app.route('/chart.js')
def serve_chart():
    return send_from_directory('frontend', 'chart.js')

@app.route('/api/send-sms', methods=['POST'])
def send_sms():
    try:
        from twilio.rest import Client
        TWILIO_SID = os.environ.get('TWILIO_SID', '')
        TWILIO_TOKEN = os.environ.get('TWILIO_TOKEN', '')
        TWILIO_NUMBER = os.environ.get('TWILIO_NUMBER', '')
        YOUR_NUMBER = os.environ.get('YOUR_NUMBER', '')
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
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        for product in expiring:
            client.messages.create(
                body=f"⚠️ StockTracker Alert!\nProduct: {product['name']}\nQty: {product['quantity']}\nExpiry: {product['expiry_date']}",
                from_=TWILIO_NUMBER,
                to=YOUR_NUMBER
            )
        return jsonify({"message": f"✅ SMS sent for {len(expiring)} products!"})
    except Exception as e:
        print(f"SMS error: {e}")
        return jsonify({"message": f"❌ SMS error: {str(e)}"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)