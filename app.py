import random
import time
import json
from flask import Flask, render_template, jsonify, Response, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# --- Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crypto_v3.db' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'amdox-intern-secret-key' 

db = SQLAlchemy(app)
CORS(app) 

# --- Database Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(100), default='New User')
    phone = db.Column(db.String(20), default='')
    country = db.Column(db.String(50), default='')
    joined_date = db.Column(db.String(20), default=lambda: time.strftime("%Y-%m-%d"))

class Coin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    change_24h = db.Column(db.Float, nullable=False)

# --- Helper: Seed Database ---
def seed_data():
    if not Coin.query.first():
        coins = [
            Coin(symbol='BTC', name='Bitcoin', price=45581.00, change_24h=-1.02),
            Coin(symbol='ETH', name='Ethereum', price=1767.81, change_24h=1.5),
            Coin(symbol='SOL', name='Solana', price=581.85, change_24h=9.25),
            Coin(symbol='BSD', name='Main USD', price=821.85, change_24h=1.50)
        ]
        db.session.add_all(coins)
        
        # Create a default demo user
        if not User.query.filter_by(email='admin@amdox.com').first():
            demo_user = User(
                email='admin@amdox.com',
                password_hash=generate_password_hash('password'),
                full_name='Om Shri Patel',
                country='India',
                phone='+91 98765 43210'
            )
            db.session.add(demo_user)
            
        db.session.commit()
        print("Database seeded!")

# --- Helper: Simulation Logic (SSE) ---
def get_market_updates():
    coins = Coin.query.all()
    updates = []
    for coin in coins:
        change = random.uniform(-0.05, 0.05) * (coin.price * 0.001) 
        coin.price += change
        coin.change_24h += random.uniform(-0.1, 0.1)
        updates.append({
            'symbol': coin.symbol,
            'price': round(coin.price, 2),
            'change': round(coin.change_24h, 2)
        })
    db.session.commit()
    return updates

# --- Routes: Pages ---
@app.route('/')
def home():
    return render_template('index.html')

# --- Routes: Authentication ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data.get('email')).first()
    if user and check_password_hash(user.password_hash, data.get('password')):
        session['user_id'] = user.id
        return jsonify({'success': True, 'message': 'Login successful'})
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({'success': False, 'message': 'Email already exists'}), 400
    
    new_user = User(
        email=data.get('email'),
        password_hash=generate_password_hash(data.get('password')),
        full_name=data.get('full_name', 'Trader')
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Account created!'})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'success': True})

# --- Routes: Profile Management ---
@app.route('/api/user-details', methods=['GET', 'POST'])
def user_details():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        data = request.json
        user.full_name = data.get('full_name', user.full_name)
        user.phone = data.get('phone', user.phone)
        user.country = data.get('country', user.country)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Profile updated'})

    return jsonify({
        'email': user.email,
        'full_name': user.full_name,
        'phone': user.phone,
        'country': user.country,
        'joined': user.joined_date
    })

# --- Routes: Real-Time Stream (SSE) ---
@app.route('/stream')
def stream():
    def generate():
        with app.app_context():
            while True:
                updates = get_market_updates()
                json_data = json.dumps({'coins': updates})
                yield f"data: {json_data}\n\n"
                time.sleep(2)
    return Response(generate(), mimetype='text/event-stream')

# --- Routes: Analytics Data ---
@app.route('/api/analytics-data')
def get_analytics_data():
    hist_labels = ["$0-100", "$100-500", "$500-1k", "$1k-5k", "$5k+"]
    hist_data = [random.randint(5, 50) for _ in range(5)]
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
    buy_vol = [random.randint(20, 100) for _ in range(6)]
    sell_vol = [random.randint(20, 100) for _ in range(6)]
    portfolio = {'labels': ['BTC', 'ETH', 'SOL', 'USDT'], 'data': [40, 30, 20, 10]}

    return jsonify({
        'histogram': {'labels': hist_labels, 'data': hist_data},
        'stacked': {'labels': months, 'buy': buy_vol, 'sell': sell_vol},
        'portfolio': portfolio
    })

# --- Routes: Initial Load ---
@app.route('/api/initial-data')
def get_initial_data():
    coins = Coin.query.all()
    data = [{'symbol': c.symbol, 'name': c.name, 'price': round(c.price, 2), 'change': c.change_24h} for c in coins]
    chart_data = [round(45000 + (random.random()-0.5)*1000, 2) for _ in range(24)]
    return jsonify({'market': data, 'chart': chart_data})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_data()
    app.run(debug=True, port=5000, threaded=True)