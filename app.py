```python
from flask import Flask, render_template_string, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "change-this-demo-secret"

DB = "ecommerce.db"

PRODUCTS = [
    {"id": 1, "name": "Wireless Headphones", "price": 1299,
     "emoji": "🎧", "category": "Electronics"},
    {"id": 2, "name": "Smart Watch", "price": 1999,
     "emoji": "⌚", "category": "Electronics"},
    {"id": 3, "name": "Casual Sneakers", "price": 1499,
     "emoji": "👟", "category": "Fashion"},
    {"id": 4, "name": "Backpack", "price": 899,
     "emoji": "🎒", "category": "Accessories"},
    {"id": 5, "name": "Sunglasses", "price": 599,
     "emoji": "🕶️", "category": "Accessories"},
    {"id": 6, "name": "Smartphone", "price": 12999,
     "emoji": "📱", "category": "Electronics"},
]

def connect_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                items TEXT NOT NULL,
                total REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>ShopEase | Online Store</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f5f7fb;
            color: #202b3c;
        }
        header {
            background: #172554;
            color: white;
            padding: 20px 7%;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }
        header h2 { margin: 0; }
        header a {
            color: white;
            text-decoration: none;
            margin-left: 18px;
        }
        .hero {
            padding: 48px 7%;
            background: linear-gradient(120deg, #dbeafe, #dcfce7);
        }
        .hero h1 { font-size: 36px; margin: 0 0 12px; }
        .hero p { color: #475569; }
        .container { padding: 30px 7%; }
        .products {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 20px;
        }
        .card {
            background: white;
            border-radius: 14px;
            padding: 20px;
            box-shadow: 0 4px 14px #0000000b;
            text-align: center;
        }
        .emoji { font-size: 65px; margin: 10px; }
        .category { color: #64748b; font-size: 13px; }
        .price { color: #15803d; font-size: 21px; font-weight: bold; }
        button, .btn {
            display: inline-block;
            background: #2563eb;
            color: white;
            border: none;
            padding: 11px 17px;
            border-radius: 7px;
            cursor: pointer;
            text-decoration: none;
            font-size: 14px;
        }
        button:hover, .btn:hover { background: #1d4ed8; }
        .remove { background: #dc2626; }
        .cart-row {
            background: white;
            margin: 12px 0;
            padding: 18px;
            border-radius: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }
        .notice {
            padding: 15px;
            border-radius: 8px;
            background: #dcfce7;
            color: #166534;
            margin-bottom: 20px;
        }
        footer {
            padding: 25px;
            text-align: center;
            color: #64748b;
        }
        @media(max-width: 500px) {
            .hero h1 { font-size: 28px; }
            header { padding: 18px 5%; }
            .container { padding: 22px 5%; }
        }
    </style>
</head>
<body>
<header>
    <h2>🛍️ ShopEase</h2>
    <nav>
        <a href="/">Home</a>
        <a href="/cart">Cart ({{ count }})</a>
    </nav>
</header>

{% if page == 'home' %}
<section class="hero">
    <h1>Discover Your Next Favourite</h1>
    <p>Great products. Simple shopping. Happy customers.</p>
    <a class="btn" href="#products">Shop Now</a>
</section>
<div class="container" id="products">
    <h2>Featured Products</h2>
    {% if message %}
        <div class="notice">{{ message }}</div>
    {% endif %}
    <div class="products">
        {% for p in products %}
        <div class="card">
            <div class="emoji">{{ p.emoji }}</div>
            <p class="category">{{ p.category }}</p>
            <h3>{{ p.name }}</h3>
            <p class="price">₹{{ p.price }}</p>
            <form action="/add/{{ p.id }}" method="post">
                <button type="submit">Add to Cart</button>
            </form>
        </div>
        {% endfor %}
    </div>
</div>

{% elif page == 'cart' %}
<div class="container">
    <h2>🛒 Your Shopping Cart</h2>
    {% if message %}
        <div class="notice">{{ message }}</div>
    {% endif %}
    {% if items %}
        {% for item in items %}
        <div class="cart-row">
            <div>
                <strong>{{ item.name }}</strong><br>
                ₹{{ item.price }} × {{ item.qty }}
            </div>
            <div>
                <strong>₹{{ item.price * item.qty }}</strong>
                <form action="/remove/{{ item.id }}" method="post"
                      style="display:inline">
                    <button class="remove" type="submit">Remove</button>
                </form>
            </div>
        </div>
        {% endfor %}
        <h2>Total: ₹{{ total }}</h2>
        <form action="/checkout" method="post">
            <button type="submit">Place Demo Order</button>
        </form>
    {% else %}
        <p>Your cart is empty. Start shopping!</p>
        <a class="btn" href="/">Browse Products</a>
    {% endif %}
</div>

{% elif page == 'success' %}
<div class="container">
    <div class="notice">
        <h2>✅ Order Placed Successfully!</h2>
        <p>Your demo order number is #{{ order_id }}.</p>
        <p>Total: ₹{{ total }}</p>
    </div>
    <a class="btn" href="/">Continue Shopping</a>
    <h3>Recent Demo Orders</h3>
    {% for order in orders %}
        <p>Order #{{ order.id }} — ₹{{ order.total }}</p>
    {% endfor %}
</div>
{% endif %}

<footer>© 2026 ShopEase | Student E-Commerce Project</footer>
</body>
</html>
"""

def get_cart():
    return session.get("cart", {})

def cart_details():
    cart = get_cart()
    items = []
    total = 0

    for p in PRODUCTS:
        qty = int(cart.get(str(p["id"]), 0))
        if qty > 0:
            item = dict(p)
            item["qty"] = qty
            items.append(item)
            total += p["price"] * qty

    return items, total

@app.route("/")
def home():
    message = session.pop("message", "")
    return render_template_string(
        PAGE, page="home", products=PRODUCTS,
        count=sum(get_cart().values()), message=message
    )

@app.route("/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    if not any(p["id"] == product_id for p in PRODUCTS):
        return "Product not found", 404

    cart = get_cart()
    key = str(product_id)
    cart[key] = min(int(cart.get(key, 0)) + 1, 20)
    session["cart"] = cart
    session["message"] = "Product added to your cart!"
    return redirect(url_for("home"))

@app.route("/cart")
def cart():
    items, total = cart_details()
    message = session.pop("message", "")
    return render_template_string(
        PAGE, page="cart", items=items, total=total,
        count=sum(get_cart().values()), message=message
    )

@app.route("/remove/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):
    cart = get_cart()
    cart.pop(str(product_id), None)
    session["cart"] = cart
    session["message"] = "Product removed from cart."
    return redirect(url_for("cart"))

@app.route("/checkout", methods=["POST"])
def checkout():
    items, total = cart_details()

    if not items:
        return redirect(url_for("cart"))

    summary = ", ".join(
        f"{item['name']} x {item['qty']}" for item in items
    )

    with connect_db() as conn:
        cursor = conn.execute(
            "INSERT INTO orders (items, total) VALUES (?, ?)",
            (summary, total)
        )
        order_id = cursor.lastrowid
        orders = conn.execute(
            "SELECT id, total FROM orders ORDER BY id DESC LIMIT 5"
        ).fetchall()

    session["cart"] = {}

    return render_template_string(
        PAGE, page="success", order_id=order_id,
        total=total, orders=orders, count=0
    )

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
```