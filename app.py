from flask import Flask, request, jsonify, render_template_string, redirect, send_file
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo
import qrcode
from io import BytesIO
import urllib.parse
import json

from flask_socketio import SocketIO

app = Flask(__name__)

socketio = SocketIO(app, cors_allowed_origins="*")
@app.route("/health")
def health():
    return "OK", 200

@app.route("/order_data/<int:id>")
def order_data(id):
    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()

    o = c.execute("SELECT * FROM orders WHERE id=?", (id,)).fetchone()
    conn.close()

    items = json.loads(o[2]) if o[2] else []

    food = [i["name"] for i in items if i.get("category") == "food"]
    drinks = [i["name"] for i in items if i.get("category") == "drink"]

    return jsonify({
        "id": o[0],
        "name": o[1],
        "table": o[4],
        "status": o[5],
        "food": food,
        "drinks": drinks
    })
    
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
        name TEXT,
        items TEXT,
        total INTEGER,
        table_no TEXT,
        status TEXT,
        datetime TEXT
    )''')

    if c.execute("SELECT COUNT(*) FROM menu").fetchone()[0] == 0:
        items = [
    # 🍽️ FOOD
    ("Frango Peri Peri", 400, "food"),
    ("Frango Grelhado", 380, "food"),
    ("Frango Frito", 350, "food"),
    ("Asas Picantes", 300, "food"),
    ("Hambúrguer Clássico", 250, "food"),
    ("Cheeseburger Duplo", 320, "food"),
    ("Pizza Margherita", 450, "food"),
    ("Pizza Frango", 500, "food"),
    ("Sanduíche de Atum", 220, "food"),
    ("Batata Frita Grande", 180, "food"),
    ("Arroz com Frango", 280, "food"),
    ("Salada Mista", 200, "food"),

    # 🍹 DRINKS
    ("Cerveja 350ml", 120, "drink"),
    ("Cerveja 500ml", 150, "drink"),
    ("Refrigerante Cola", 80, "drink"),
    ("Fanta Laranja", 80, "drink"),
    ("Sprite", 80, "drink"),
    ("Água Mineral", 50, "drink"),
    ("Sumo Natural Manga", 120, "drink"),
    ("Sumo Natural Laranja", 120, "drink"),
    ("Vinho Tinto", 250, "drink"),
    ("Vinho Branco", 250, "drink"),
    ("Whisky Dose", 180, "drink"),
    ("Gin Tónico", 220, "drink"),
        ]
        c.executemany("INSERT INTO menu VALUES (NULL,?,?,?)", items)

    conn.commit()
    conn.close()

init_db()

# ---------------- SAFE DB UPGRADE ----------------
def ensure_phone_column():
    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE orders ADD COLUMN phone TEXT")
    except:
        pass
    conn.commit()
    conn.close()

ensure_phone_column()

# ---------------- CUSTOMER UI ----------------
@app.route("/")
def menu():
    table = request.args.get("table", "1")

    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    items = c.execute("SELECT * FROM menu").fetchall()
    conn.close()

    return render_template_string("""
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
body{
    background:#0b0b0b;
    color:#fff;
    font-family:system-ui;
    padding:16px;
}

/* HEADER */
h1{
    text-align:center;
    color:#ff4d4d;
    font-size:34px;
    margin-bottom:5px;
}

p{
    text-align:center;
    color:#aaa;
}

/* INPUTS */
input{
    width:100%;
    padding:14px;
    margin-bottom:10px;
    border-radius:10px;
    border:1px solid #2a2a2a;
    background:#141414;
    color:#fff;
}

/* SECTION TITLE */
h2{
    margin-top:25px;
    font-size:20px;
    color:#ccc;
}

/* CARD */
.card{
    background:#151515;
    padding:16px;
    margin:10px 0;
    border-radius:14px;
    display:flex;
    justify-content:space-between;
    align-items:center;
    border:1px solid #222;
    transition:0.2s;
}

.card:hover{
    transform:scale(1.02);
}

/* TEXT */
.card div{
    font-size:18px;
    font-weight:500;
}

.card small{
    color:#888;
}

/* BUTTON */
button{
    background:#ff4d4d;
    border:none;
    padding:10px 16px;
    border-radius:10px;
    font-weight:bold;
    font-size:14px;
    transition:0.2s;
}

button:hover{
    background:#ff3333;
}

button:active{
    transform:scale(0.95);
}

/* CART */
.cart-box{
    position:fixed;
    bottom:0;
    left:0;
    width:100%;
    background:#0f0f0f;
    padding:14px;
    border-top:1px solid #222;
}

/* CART TITLE */
.cart-box h3{
    margin:4px 0;
    font-size:16px;
}

/* ITEMS */
#cart li{
    font-size:14px;
    color:#ccc;
}

/* TOTAL */
#total{
    font-size:20px;
    color:#00ff88;
    margin-top:5px;
}

/* ACTION BUTTONS */
.cart-box button{
    width:100%;
    margin-top:8px;
    font-size:16px;
}

/* SECOND BUTTON */
.cart-box button:last-child{
    background:#1f1f1f;
    color:#fff;
}

</style>

<h1>🌶️ {{name}}</h1>

<p><b>Mesa {{table}}</b></p>

<input id="name" placeholder="Seu nome">
<input id="phone" placeholder="WhatsApp (opcional)">

<h2>🍽️ Comida</h2>
{% for i in items if i[3]=='food' %}
<div class="card">
<div>{{i[1]}}<br><small>{{i[2]}} MZN</small></div>
<button onclick="add('{{i[1]}}',{{i[2]}})">Adicionar</button>
</div>
{% endfor %}

<h2>🍺 Bebidas</h2>
{% for i in items if i[3]=='drink' %}
<div class="card">
<div>{{i[1]}}<br><small>{{i[2]}} MZN</small></div>
<button onclick="add('{{i[1]}}',{{i[2]}})">Adicionar</button>
</div>
{% endfor %}

<div class="cart-box">
<h3>🍽️ Bandeja</h3>
<ul id="cart"></ul>
<h3 id="total">0 MZN</h3>

<button style="width:100%" onclick="order()">📦 Enviar Pedido</button>
<button style="width:100%;margin-top:10px;" onclick="goTrack()">
📦 Ver meu pedido
</button>
</div>

<script>
if(window.innerWidth < 500){
    document.body.style.zoom = "1.2";
}
</script>

<script>
let cart = [];
let total = 0;

function add(n, p){
    cart.push(n);
    total += p;

    document.getElementById("cart").innerHTML =
        cart.map(i => "<li>" + i + "</li>").join("");

    document.getElementById("total").innerText = total + " MZN";
}

function order(){
    if(cart.length == 0){
        alert("Carrinho vazio!");
        return;
    }

    fetch("/order", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({
            name: document.getElementById("name").value,
            phone: document.getElementById("phone").value,
            items: cart,
            total: total,
            table: "{{table}}"
        })
    })
    .then(r => r.json())
    .then(d => {
        alert("Pedido enviado!");
        localStorage.setItem("lastOrderId", d.id);  // ✅ SAVE ID
        window.location = "/track/" + d.id;
    });
}

// ✅ BUTTON TO RETURN TO TRACK PAGE
function goTrack(){
    let id = localStorage.getItem("lastOrderId");

    if(id){
        window.location = "/track/" + id;
    }else{
        alert("Nenhum pedido encontrado!");
    }
}
</script>
""", items=items, name=NAME, table=table)

# ---------------- ORDER ----------------
import json

@app.route("/order", methods=["POST"])
def order():
    d = request.json

    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()

    # 🔹 Build items with category
    items_with_category = []

    for item in d["items"]:
        row = c.execute(
            "SELECT name, category FROM menu WHERE name=?",
            (item,)
        ).fetchone()

        if row:
            items_with_category.append({
                "name": row[0],
                "category": row[1]
            })

    # 🔹 Insert order
    c.execute(
        "INSERT INTO orders VALUES (NULL,?,?,?,?,?,?,?)",
(
    d["name"],
    json.dumps(items_with_category),
    d["total"],
    d["table"],
    "Pendente",
    datetime.now(ZoneInfo("Africa/Maputo")).strftime("%d-%m-%Y %H:%M"),
d.get("phone", "")
)
    )  
    oid = c.lastrowid
    conn.commit()
    conn.close()
    
    socketio.emit("new_order", {"id": oid})

    return jsonify({"id": oid})

# ---------------- TRACK ----------------    
@app.route("/track/<int:id>")
def track(id):
    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    o = c.execute("SELECT * FROM orders WHERE id=?", (id,)).fetchone()
    conn.close()

    return render_template_string("""
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>

<script>
const socket = io();

socket.on("status_updated", function(data){
    if(data.id == {{o[0]}}){
        setTimeout(() => location.reload(), 300);
    }
});
</script>

<style>  
/* ✅ AUTO SCALING TEXT */
h1{
    font-size: 3rem;
}

h2{
    font-size: 2.2rem;
}

p{
    font-size: 1.4rem;
}

button{
    font-size: 1.3rem;
}
/* 🔥 AUTO SCALE BASE */
html {
    font-size: 16px;
}

/* 📱 Small phones */
@media (max-width: 480px) {
    html {
        font-size: 18px;
    }
}

/* 📱 Large phones */
@media (min-width: 481px) and (max-width: 768px) {
    html {
        font-size: 20px;
    }
}

/* 💻 Tablets */
@media (min-width: 769px) and (max-width: 1024px) {
    html {
        font-size: 22px;
    }
}

/* 🖥️ Desktop / TV */
@media (min-width: 1025px) {
    html {
        font-size: 24px;
    }
}
body{
    background:#0f0f0f;
    color:white;
    text-align:center;
    font-family:Arial;
    padding:25px;
    font-size:22px;
}

/* 🔥 BIGGER BOX */
.box{
    background:#1c1c1c;
    padding:30px;
    border-radius:16px;
    max-width:600px;
    margin:auto;
}

/* 🔥 BIG TEXT */
h1{
    font-size:48px;
}

h2{
    font-size:36px;
    margin-top:20px;
}

p{
    font-size:26px;
}

/* 🔥 BIG BUTTONS */
button{  
    padding:18px 26px;  
    border:none;  
    border-radius:12px;  
    margin:12px;  
    font-size:22px;  
    font-weight:bold;
}  

.yes{background:#28a745;color:white}  
.no{background:#dc3545;color:white}  
</style>  

<h1>📦 Pedido</h1>  

<div class="box">  

<p><b>Nome:</b> {{o[1]}}</p>  
<p><b>Mesa:</b> {{o[4]}}</p>  

<!-- 🔥 STATUS: Cliente chamou -->
{% if o[5] == "Cliente chamou" %}
<h2 style="color:#ffc107;font-size:40px;">
📢 Cliente chamou a cozinha...
</h2>
{% endif %}

<!-- 🔥 STATUS FLOW -->
{% if o[5] == "Aguardando Confirmação" %}
    <h2 style="font-size:40px;">Posso preparar o seu pedido?</h2>

    <button class="yes" onclick="confirmChoice('yes')">Sim</button>  
    <button class="no" onclick="confirmChoice('no')">Não</button>

{% elif o[5] == "Cancelado" %}
    <h2 style="color:#dc3545;font-size:40px;">Pedido cancelado</h2>

{% elif o[5] == "Preparando" %}
    <h2 style="color:#007bff;font-size:40px;">Em preparação...</h2>

{% elif o[5] == "Concluído" %}
    <h2 style="color:#28a745;font-size:40px;">Pronto!</h2>

{% elif o[5] == "Recebido, a caminho" %}
    <h2 style="color:#17a2b8;font-size:40px;">
    🚶‍♂️ Recebido! A caminho...
    </h2>
{% endif %}

<p><b>Data:</b> {{o[6]}}</p>  

</div>  

<script>  

function callWaiter(){  
    fetch("/call_waiter",{  
        method:"POST",  
        headers:{"Content-Type":"application/json"},  
        body:JSON.stringify({  
            id: {{o[0]}}  
        })  
    }).then(()=>{  
        alert("Pedido enviado para a cozinha!");  
        location.reload();  
    });  
}  

function confirmChoice(choice){  
    fetch("/client_confirm",{  
        method:"POST",  
        headers:{"Content-Type":"application/json"},  
        body:JSON.stringify({  
            id: {{o[0]}},  
            choice: choice  
        })  
    }).then(()=>location.reload());  
}  

</script>  

<button onclick="window.location='/?table={{o[4]}}'">
Novo Pedido
</button>

<button onclick="callWaiter()" style="background:#ffc107;color:black;">
📢 Consultar
</button>
""", o=o)
# ---------------- CLIENT CONFIRM ----------------
@app.route("/client_confirm", methods=["POST"])
def client_confirm():
    d = request.json

    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()

    if d["choice"] == "yes":
        c.execute(
            "UPDATE orders SET status=? WHERE id=?",
            ("Preparando", d["id"])
        )
    else:
        c.execute(
            "UPDATE orders SET status=? WHERE id=?",
            ("Cancelado", d["id"])
        )

    conn.commit()
    conn.close()

    return jsonify({"ok": True})

# ---------------- CUSTOMER ENQUIRY ----------------
@app.route("/call_waiter", methods=["POST"])
def call_waiter():
    d = request.json

    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()

    # Update status OR add flag
    c.execute(
        "UPDATE orders SET status=? WHERE id=?",
        ("Cliente chamou", d["id"])
    )

    conn.commit()
    conn.close()

    return jsonify({"ok": True})
# ---------------- KITCHEN ----------------
@app.route("/kitchen")
def kitchen():
    import json

    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()

    raw_active = c.execute(
        "SELECT * FROM orders WHERE status!='Concluído' ORDER BY id DESC"
    ).fetchall()

    raw_done = c.execute(
        "SELECT * FROM orders WHERE status='Concluído' ORDER BY id DESC LIMIT 20"
    ).fetchall()

    def process_orders(rows):
        result = []
        for o in rows:
            try:
                items = json.loads(o[2])
            except:
                items = []

            food = [i["name"] for i in items if i.get("category") == "food"]
            drinks = [i["name"] for i in items if i.get("category") == "drink"]

            result.append({
                "id": o[0],
                "name": o[1],
                "table": o[4],
                "status": o[5],
                "food": food,
                "drinks": drinks
            })
        return result

    active = process_orders(raw_active)
    done = process_orders(raw_done)

    conn.close()

    return render_template_string("""
<style>
body{
    background:#050505;
    color:white;
    font-family:system-ui;
    padding:20px;
}

h1{
    text-align:center;
    color:#ffcc00;
    font-size:46px;
}

h2{
    font-size:30px;
    margin-top:40px;
    border-left:6px solid #ff4d4d;
    padding-left:12px;
}

.grid{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(350px,1fr));
    gap:20px;
}

.order{
    background:#121212;
    padding:22px;
    border-radius:18px;
    font-size:22px;
}

.status{
    padding:12px;
    border-radius:12px;
    font-weight:bold;
    text-align:center;
    margin:12px 0;
    font-size:18px;
}

.pending{background:#ffc107;color:black}
.preparing{background:#00bcd4}
.done{background:#28a745}

button{
    margin:6px;
    padding:12px 16px;
    border:none;
    border-radius:10px;
    font-size:16px;
    font-weight:bold;
}

.yellow{background:#ffc107}
.green{background:#28a745;color:white}
.red{background:#dc3545;color:white}

button:active{
    transform:scale(0.95);
}
</style>

<h1>🍹 Bar e Cozinha</h1>

<h2>📌 Ativos</h2>
<div class="grid">
{% for o in active %}
<div class="order">

<b style="font-size:26px;">Mesa {{o.table}}</b><br>
👤 {{o.name}}<br><br>

{% if o.food %}
<div>
<b>🍳 Comida:</b><br>
{% for f in o.food %}
• {{f}}<br>
{% endfor %}
</div>
{% endif %}

{% if o.drinks %}
<div style="margin-top:10px;">
<b>🍹 Bebidas:</b><br>
{% for d in o.drinks %}
• {{d}}<br>
{% endfor %}
</div>
{% endif %}

<div class="status
{% if o.status=='Pendente' %}pending{% endif %}
{% if o.status=='Preparando' %}preparing{% endif %}
{% if o.status=='Concluído' %}done{% endif %}
{% if o.status=='Cliente chamou' %}pending{% endif %}
">
{{o.status}}
</div>

{% if o.status=='Cliente chamou' %}
<div style="color:#ffc107;font-weight:bold;">
⚠️ Cliente está a consultar!
</div>

<button class="green"
onclick="update({{o.id}},'Recebido, a caminho')">
✅ Responder Cliente
</button>
{% endif %}

<button class="yellow" onclick="update({{o.id}},'Aguardando Confirmação')">
Confirmar Pedido
</button>
<button class="green" onclick="update({{o.id}},'Concluído')">Concluir</button>
<button class="red" onclick="window.open('/receipt_any/{{o.id}}')">🧾</button>
<button onclick="window.open('/send_whatsapp/{{o.id}}')">📲 WhatsApp</button>

</div>
{% endfor %}
</div>

<h2>✅ Concluídos</h2>
<div class="grid">
{% for o in done %}
<div class="order" id="order-{{o.id}}">

<b>Mesa {{o.table}}</b><br>
👤 {{o.name}}<br><br>

<div class="status done">Concluído</div>

<button onclick="window.open('/receipt_any/{{o.id}}')">🧾</button>
<button onclick="window.open('/send_whatsapp/{{o.id}}')">📲</button>

</div>
{% endfor %}
</div>

<script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>

<script>
const socket = io();

// 🔔 SOUND (optional but useful)
const audio = new Audio("https://www.soundjay.com/buttons/beep-01a.mp3");

// 🔥 NEW ORDER (instant)
socket.on("new_order", function(data){
    audio.play();

    fetch("/order_data/" + data.id)
    .then(res => res.json())
    .then(order => addOrder(order));
});

// 🔥 STATUS UPDATE (instant)
socket.on("status_updated", function(data){
    let el = document.getElementById("order-" + data.id);
    if(!el) return;

    let statusBox = el.querySelector(".status");
    statusBox.innerText = data.status;

    statusBox.className = "status";
    if(data.status === "Pendente") statusBox.classList.add("pending");
    if(data.status === "Preparando") statusBox.classList.add("preparing");
    if(data.status === "Concluído") statusBox.classList.add("done");
    if(data.status === "Recebido, a caminho") statusBox.classList.add("preparing");

    if(data.status === "Concluído"){
        el.remove();
    }
});

// 🔥 ADD ORDER
function addOrder(o){
    const container = document.querySelector(".grid");

    let food = o.food.length 
        ? "<b>🍳 Comida:</b><br>• " + o.food.join("<br>• ") 
        : "";

    let drinks = o.drinks.length 
        ? "<br><b>🍹 Bebidas:</b><br>• " + o.drinks.join("<br>• ") 
        : "";

    const html = `
    <div class="order" id="order-${o.id}">
        <b style="font-size:26px;">Mesa ${o.table}</b><br>
        👤 ${o.name}<br><br>

        ${food}
        ${drinks}

        <div class="status pending">Pendente</div>

        <button class="yellow" onclick="update(${o.id},'Aguardando Confirmação')">
        Confirmar Pedido
        </button>

        <button class="green" onclick="update(${o.id},'Concluído')">
        Concluir
        </button>
    </div>
    `;

    container.insertAdjacentHTML("afterbegin", html);
}

// EXISTING UPDATE
function update(id,status){
    fetch("/update_status",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({id:id,status:status})
    });
}
</script>

""", active=active, done=done)

# ---------------- UPDATE STATUS ----------------
@app.route("/update_status", methods=["POST"])
def update_status():
    d = request.json

    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()

    c.execute(
        "UPDATE orders SET status=? WHERE id=?",
        (d["status"], d["id"])
    )

    conn.commit()
    conn.close()

    # ✅ SAME INDENT LEVEL AS conn.commit()
    socketio.emit("status_updated", {
        "id": d["id"],
        "status": d["status"]
    })

    return jsonify({"ok": True})
# ---------------- QR ----------------
@app.route("/qr/<int:table>")
def qr(table):
    url = request.host_url + "?table=" + str(table)
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

@app.route("/qr_tables")
def qr_tables():
    return render_template_string("""
<h1>📱 QR Codes Mesas</h1>
{% for i in range(1,11) %}
<div>
<h3>Mesa {{i}}</h3>
<img src="/qr/{{i}}" width="200">
</div>
{% endfor %}
""")

# ---------------- WHATSAPP ---------------
@app.route("/send_whatsapp/<int:id>")
def send_whatsapp(id):
    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    o = c.execute("SELECT * FROM orders WHERE id=?", (id,)).fetchone()
    conn.close()

    phone = ""
    try:
        phone = o[7]
    except:
        pass

    if not phone:
        return "<h3>❌ Cliente não forneceu WhatsApp</h3>"

    # limpar número
    phone = phone.replace(" ", "").replace("+", "")

    # adicionar código de Moçambique
    if phone.startswith("0"):
        phone = "258" + phone[1:]
    elif not phone.startswith("258"):
        phone = "258" + phone

    msg = f"""
🌶️ Peri Peri

Nome: {o[1]}
Mesa: {o[4]}

Itens:
{o[2]}

Total: {o[3]} MZN
Status: {o[5]}
Data: {o[6]}

Obrigado!
"""

    url = "https://wa.me/" + phone + "?text=" + urllib.parse.quote(msg)
    return redirect(url)
# ---------------- RUN ----------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
