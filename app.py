from flask import Flask, request, jsonify, render_template_string
import sqlite3
from datetime import datetime

app = Flask(__name__)

RESTAURANT_NAME = "Peri Peri 🌶️"

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS menu (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price INTEGER,
        category TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        items TEXT,
        total INTEGER,
        table_no TEXT,
        time TEXT,
        status TEXT
    )''')

    # default menu
    c.execute("SELECT COUNT(*) FROM menu")
    if c.fetchone()[0] == 0:
        items = [
            ("Peri Peri Chicken", 400, "food"),
            ("Spicy Wings", 300, "food"),
            ("Burger", 250, "food"),
            ("Beer", 120, "alcohol"),
            ("Red Wine", 250, "alcohol"),
            ("Whisky Shot", 180, "alcohol")
        ]
        c.executemany("INSERT INTO menu (name, price, category) VALUES (?, ?, ?)", items)

    conn.commit()
    conn.close()

init_db()

# ---------------- CUSTOMER PAGE ----------------
@app.route("/")
def menu():
    table = request.args.get("table", "1")

    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    c.execute("SELECT * FROM menu")
    items = c.fetchall()
    conn.close()

    return render_template_string("""
    <html>
    <head>
    <style>
        body { background:#111; color:#fff; font-family:Arial; padding:15px;}
        h1 { color:#ff4d4d;}
        .item { background:#222; margin:8px; padding:10px; border-radius:8px;}
        button { background:#ff4d4d; color:white; border:none; padding:5px;}
    </style>
    </head>

    <body>
    <h1>🔥 {{name}}</h1>
    <p>Table: {{table}}</p>

    <h2>🍽️ Food</h2>
    {% for i in items if i[3]=='food' %}
        <div class="item">
            {{i[1]}} - {{i[2]}} MZN
            <button onclick="add('{{i[1]}}', {{i[2]}})">Add</button>
        </div>
    {% endfor %}

    <h2>🍺 Alcohol</h2>
    {% for i in items if i[3]=='alcohol' %}
        <div class="item">
            {{i[1]}} - {{i[2]}} MZN
            <button onclick="add('{{i[1]}}', {{i[2]}})">Add</button>
        </div>
    {% endfor %}

    <h2>🛒 Cart</h2>
    <ul id="cart"></ul>
    <h3 id="total">0</h3>
    <button onclick="order()">Place Order</button>

    <script>
    let cart = [];
    let total = 0;

    function add(name, price){
        cart.push(name);
        total += price;
        document.getElementById("cart").innerHTML += "<li>"+name+"</li>";
        document.getElementById("total").innerText = total + " MZN";
    }

    function order(){
        fetch("/order", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({
                items: cart,
                total: total,
                table: "{{table}}"
            })
        }).then(()=>alert("Order sent!"));
    }
    </script>
    </body>
    </html>
    """, items=items, name=RESTAURANT_NAME, table=table)

# ---------------- PLACE ORDER ----------------
@app.route("/order", methods=["POST"])
def order():
    data = request.json

    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()

    c.execute("INSERT INTO orders (items,total,table_no,time,status) VALUES (?,?,?,?,?)",
              (str(data["items"]), data["total"], data["table"], datetime.now().strftime("%H:%M"), "pending"))

    conn.commit()
    conn.close()

    return jsonify({"ok": True})

# ---------------- KITCHEN SCREEN ----------------
@app.route("/kitchen")
def kitchen():
    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    c.execute("SELECT * FROM orders ORDER BY id DESC")
    orders = c.fetchall()
    conn.close()

    return render_template_string("""
    <meta http-equiv="refresh" content="5">
    <h1>👨‍🍳 Kitchen - {{name}}</h1>

    {% for o in orders %}
        <div style="border:1px solid #000; margin:10px; padding:10px;">
            <b>Table {{o[3]}}</b> | {{o[4]}} | {{o[5]}}<br>
            {{o[1]}}<br>
            Total: {{o[2]}} MZN
        </div>
    {% endfor %}
    """, orders=orders, name=RESTAURANT_NAME)

# ---------------- ADMIN ----------------
@app.route("/admin")
def admin():
    return """
    <h2>Admin</h2>
    <input id="id" placeholder="Item ID">
    <input id="price" placeholder="New Price">
    <button onclick="update()">Update</button>

    <script>
    function update(){
        fetch("/update", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({
                id: document.getElementById("id").value,
                price: document.getElementById("price").value
            })
        }).then(()=>alert("Updated"));
    }
    </script>
    """

@app.route("/update", methods=["POST"])
def update():
    data = request.json
    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    c.execute("UPDATE menu SET price=? WHERE id=?", (data["price"], data["id"]))
    conn.commit()
    conn.close()
    return jsonify({"ok":True})

# ---------------- SALES REPORT ----------------
@app.route("/sales")
def sales():
    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    c.execute("SELECT SUM(total) FROM orders")
    total = c.fetchone()[0]
    conn.close()

    return f"<h1>Total Sales: {total} MZN</h1>"

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()