from flask import Flask, request, jsonify, render_template_string
import sqlite3
from datetime import datetime

app = Flask(__name__)

NAME = "Peri Peri 🌶️"

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS menu (
        id INTEGER PRIMARY KEY,
        name TEXT,
        price INTEGER,
        category TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY,
        items TEXT,
        total INTEGER,
        table_no TEXT,
        status TEXT,
        time TEXT
    )''')

    if c.execute("SELECT COUNT(*) FROM menu").fetchone()[0] == 0:
        items = [
            ("Frango Peri Peri", 400, "food"),
            ("Asas Picantes", 300, "food"),
            ("Hambúrguer", 250, "food"),
            ("Cerveja", 120, "drink"),
            ("Vinho", 250, "drink"),
            ("Whisky", 180, "drink")
        ]
        c.executemany("INSERT INTO menu (name, price, category) VALUES (?,?,?)", items)

    conn.commit()
    conn.close()

init_db()

# ---------------- CUSTOMER ----------------
@app.route("/")
def menu():
    table = request.args.get("table", "1")

    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    items = c.execute("SELECT * FROM menu").fetchall()
    conn.close()

    return render_template_string("""
    <html>
    <head>
    <style>
        body {background:#111;color:#fff;font-family:sans-serif;padding:15px;}
        h1 {color:#ff4d4d;}
        .card {background:#222;padding:10px;margin:8px;border-radius:8px;}
        button {background:#ff4d4d;color:#fff;border:none;padding:6px;}
    </style>
    </head>
    <body>

    <h1>{{name}}</h1>
    <p>Mesa: {{table}}</p>

    <h2>🍗 Comida</h2>
    {% for i in items if i[3]=='food' %}
    <div class="card">
        {{i[1]}} - {{i[2]}} MZN
        <button onclick="add('{{i[1]}}',{{i[2]}})">Adicionar</button>
    </div>
    {% endfor %}

    <h2>🍺 Bebidas</h2>
    {% for i in items if i[3]=='drink' %}
    <div class="card">
        {{i[1]}} - {{i[2]}} MZN
        <button onclick="add('{{i[1]}}',{{i[2]}})">Adicionar</button>
    </div>
    {% endfor %}

    <h2>🛒 Carrinho</h2>
    <ul id="cart"></ul>
    <h3 id="total">0</h3>

    <button onclick="order()">Enviar Pedido</button>

    <script>
    let cart=[];let total=0;

    function add(n,p){
        cart.push(n); total+=p;
        cartEl.innerHTML += "<li>"+n+"</li>";
        totalEl.innerText=total+" MZN";
    }

    function order(){
        fetch("/order",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({items:cart,total:total,table:"{{table}}"})})
        .then(()=>alert("Pedido enviado!"));
    }
    </script>

    </body></html>
    """, items=items, name=NAME, table=table)

# ---------------- ORDER ----------------
@app.route("/order", methods=["POST"])
def order():
    data=request.json
    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()

    c.execute("INSERT INTO orders (items,total,table_no,status,time) VALUES (?,?,?,?,?)",
              (str(data["items"]),data["total"],data["table"],"pending",datetime.now().strftime("%H:%M")))

    conn.commit(); conn.close()
    return jsonify(ok=True)

# ---------------- KITCHEN ----------------
@app.route("/kitchen")
def kitchen():
    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()
    orders=c.execute("SELECT * FROM orders WHERE status!='done' ORDER BY id DESC").fetchall()
    conn.close()

    return render_template_string("""
    <meta http-equiv="refresh" content="5">
    <h1>👨‍🍳 Cozinha</h1>

    <audio id="sound" src="https://www.soundjay.com/buttons/sounds/button-3.mp3"></audio>

    {% for o in orders %}
    <div style="padding:10px;margin:10px;
        background:
        {% if o[4]=='pending' %}orange
        {% elif o[4]=='preparing' %}yellow
        {% else %}lightgreen{% endif %};">

        <b>Mesa {{o[3]}}</b> | {{o[5]}}<br>
        {{o[1]}}<br>
        {{o[4]}}<br>

        <button onclick="update({{o[0]}},'preparing')">Preparando</button>
        <button onclick="update({{o[0]}},'done')">Concluído</button>
    </div>
    {% endfor %}

    <script>
    document.getElementById("sound").play();

    function update(id,status){
        fetch("/update_status",{method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({id:id,status:status})})
        .then(()=>location.reload());
    }
    </script>
    """, orders=orders)

# ---------------- UPDATE STATUS ----------------
@app.route("/update_status", methods=["POST"])
def update_status():
    d=request.json
    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()
    c.execute("UPDATE orders SET status=? WHERE id=?", (d["status"], d["id"]))
    conn.commit(); conn.close()
    return jsonify(ok=True)

# ---------------- RUN ----------------
if __name__=="__main__":
    app.run()
