from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from database import get_db, init_db
from datetime import date, timedelta
import smtplib
import bcrypt
import os
from twilio.rest import Client
from apscheduler.schedulers.background import BackgroundScheduler
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)
init_db()

# Config — Railway Variables-ல் இருந்து எடுக்கும்
EMAIL = os.environ.get('EMAIL', 'sarathiilangovan@gmail.com')
PASSWORD = os.environ.get('PASSWORD', 'utpu ldtu mksj xglh')
TWILIO_SID = os.environ.get('TWILIO_SID', '')
TWILIO_TOKEN = os.environ.get('TWILIO_TOKEN', '')
TWILIO_NUMBER = os.environ.get('TWILIO_NUMBER', '')
YOUR_NUMBER = os.environ.get('YOUR_NUMBER', '')

def send_email_alert(product_name, expiry_date, quantity, to_email):
    msg = MIMEMultipart()
    msg['From'] = EMAIL
    msg['To'] = to_email
    msg['Subject'] = f"⚠️ StockTracker Alert: {product_name} Expiring Soon!"
    body = f"""
    ⚠️ Expiry Alert - StockTracker

    Product  : {product_name}
    Quantity : {quantity}
    Expiry   : {expiry_date}

    Please take action before the product expires!

    - StockTracker System
    """
    msg.attach(MIMEText(body, 'plain'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.sendmail(EMAIL, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def send_sms_alert(product_name, expiry_date, quantity):
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        message = client.messages.create(
            body=f"⚠️ StockTracker Alert!\nProduct: {product_name}\nQuantity: {quantity}\nExpiry: {expiry_date}\nPlease take action!",
            from_=TWILIO_NUMBER,
            to=YOUR_NUMBER
        )
        print(f"SMS sent: {message.sid}")
        return True
    except Exception as e:
        print(f"SMS error: {e}")
        return False

def daily_alert():
    print("🔔 Running daily alert check...")
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
    if expiring:
        for product in expiring:
            send_email_alert(product['name'], product['expiry_date'], product['quantity'], EMAIL)
            send_sms_alert(product['name'], product['expiry_date'], product['quantity'])
        print(f"✅ Alert sent for {len(expiring)} products!")
    else:
        print("✅ No expiring products today!")

scheduler = BackgroundScheduler()
scheduler.add_job(daily_alert, 'cron', hour=9, minute=0)
scheduler.start()

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

@app.route('/api/send-sms', methods=['POST'])
def send_sms():
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
        send_sms_alert(product['name'], product['expiry_date'], product['quantity'])
    return jsonify({"message": f"✅ SMS sent for {len(expiring)} products!"})

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
    app.run(debug=True, host='0.0.0.0', port=5000)