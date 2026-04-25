from flask import Flask, request, jsonify, render_template_string, redirect, send_file, session
import sqlite3
from datetime import datetime
import qrcode
from io import BytesIO
import urllib.parse
from flask_socketio import SocketIO

app = Flask(__name__)
app.secret_key = "supersecret123"

# 🔥 SOCKET
socketio = SocketIO(app, cors_allowed_origins="*")

ADMIN_USER = "admin"
ADMIN_PASS = "1234"

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

    conn.commit()
    conn.close()

init_db()

# ---------------- SAFE DB ----------------
def ensure_phone():
    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE orders ADD COLUMN phone TEXT")
    except:
        pass
    conn.commit()
    conn.close()

ensure_phone()

# ---------------- ADMIN ----------------
@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.method == "POST":
        if request.form["user"] == ADMIN_USER and request.form["pass"] == ADMIN_PASS:
            session["admin"] = True
            return redirect("/kitchen")

    return """
    <h2>🔐 Login</h2>
    <form method="post">
    <input name="user"><br><br>
    <input name="pass" type="password"><br><br>
    <button>Login</button>
    </form>
    """

# ---------------- CUSTOMER ----------------
@app.route("/")
def menu():
    table = request.args.get("table","1")

    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    items = c.execute("SELECT * FROM menu").fetchall()
    conn.close()

    return render_template_string("""
<style>
body{background:#0f0f0f;color:white;font-family:Arial;padding:15px}
h1{text-align:center;color:#ff3b3b}
.card{background:#1c1c1c;padding:15px;margin:10px;border-radius:10px}
button{width:100%;padding:15px;font-size:18px;border:none;border-radius:10px;margin-top:5px}
.add{background:#ff3b3b;color:white}
.send{background:#28a745;color:white}
input{width:100%;padding:12px;margin:5px 0;border-radius:8px}
</style>

<h1>{{name}}</h1>
<p><b>Mesa {{table}}</b></p>

<input id="name" placeholder="Nome">
<input id="phone" placeholder="WhatsApp">

{% for i in items %}
<div class="card">
{{i[1]}} - {{i[2]}} MZN
<button class="add" onclick="add('{{i[1]}}',{{i[2]}})">Adicionar</button>
</div>
{% endfor %}

<h3 id="total">0 MZN</h3>
<button class="send" onclick="order()">📦 Enviar Pedido</button>

<script>
let cart=[];let total=0;

function add(n,p){
cart.push(n);
total+=p;
document.getElementById("total").innerText=total+" MZN";
}

function order(){
fetch("/order",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({
name:document.getElementById("name").value,
phone:document.getElementById("phone").value,
items:cart,
total:total,
table:"{{table}}"
})
}).then(r=>r.json()).then(d=>{
window.location="/track/"+d.id;
});
}
</script>
""", items=items, name=NAME, table=table)

# ---------------- ORDER ----------------
@app.route("/order", methods=["POST"])
def order():
    d=request.json

    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()

    c.execute("INSERT INTO orders VALUES (NULL,?,?,?,?,?,?,?)",
        (d["name"], str(d["items"]), d["total"], d["table"],
         "Aguardando Confirmação",
         datetime.now().strftime("%d-%m-%Y %H:%M"),
         d.get("phone",""))
    )

    oid=c.lastrowid
    conn.commit()
    conn.close()

    socketio.emit("new_order", {"id":oid})

    return jsonify({"id":oid})

# ---------------- TRACK ----------------
@app.route("/track/<int:id>")
def track(id):
    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()
    o=c.execute("SELECT * FROM orders WHERE id=?", (id,)).fetchone()
    conn.close()

    return render_template_string("""
<h1>📦 Pedido</h1>

<h2 id="status">{{o[5]}}</h2>

<button onclick="confirm()">✔ Confirmar</button>
<button onclick="reject()">✖ Rejeitar</button>

<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
<script>
var socket = io();

socket.on("order_update", function(data){
if(data.id == {{o[0]}}){
document.getElementById("status").innerText = data.status;
}
});

function confirm(){
window.location="/confirm_order/{{o[0]}}"
}
function reject(){
window.location="/reject_order/{{o[0]}}"
}
</script>
""", o=o)

# ---------------- CONFIRM ----------------
@app.route("/confirm_order/<int:id>")
def confirm_order(id):
    update_status_internal(id,"Confirmado pelo Cliente")
    return redirect("/track/"+str(id))

@app.route("/reject_order/<int:id>")
def reject_order(id):
    update_status_internal(id,"Rejeitado pelo Cliente")
    return redirect("/track/"+str(id))

# ---------------- KITCHEN ----------------
@app.route("/kitchen")
def kitchen():
    if not session.get("admin"):
        return redirect("/admin")

    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()
    orders=c.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    conn.close()

    return
