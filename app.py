from flask import Flask, request, jsonify, render_template_string, redirect, send_file, session
import sqlite3
from datetime import datetime
import urllib.parse

app = Flask(__name__)

app.secret_key = "supersecret123"
ADMIN_USER = "admin"
ADMIN_PASS = "1234"

NAME = "Peri Peri 🌶️"

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY,
        name TEXT,
        items TEXT,
        total INTEGER,
        table_no TEXT,
        status TEXT,
        datetime TEXT,
        phone TEXT
    )''')

    conn.commit()
    conn.close()

init_db()

# ---------------- ADMIN LOGIN ----------------
@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.method == "POST":
        if request.form.get("user") == ADMIN_USER and request.form.get("pass") == ADMIN_PASS:
            session["admin"] = True
            return redirect("/kitchen")

    return render_template_string("""
    <h2>🔐 Login</h2>
    <form method="post">
        <input name="user" placeholder="User"><br><br>
        <input name="pass" type="password" placeholder="Password"><br><br>
        <button>Login</button>
    </form>
    """)

# ---------------- CUSTOMER MENU ----------------
@app.route("/")
def menu():
    table = request.args.get("table", "1")

    return render_template_string("""
<style>
body{background:#111;color:#fff;font-family:Arial;padding:20px}
input,button{width:100%;padding:18px;margin:8px 0;font-size:18px;border-radius:10px}
button{background:#ff3b3b;color:white;border:none}
</style>

<h1>{{name}}</h1>
<h2>Mesa {{table}}</h2>

<input id="name" placeholder="Nome">
<input id="phone" placeholder="WhatsApp">

<button onclick="order()">📦 Fazer Pedido</button>

<script>
function order(){
fetch("/order",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({
name:document.getElementById("name").value,
phone:document.getElementById("phone").value,
items:["Pedido rápido"],
total:0,
table:"{{table}}"
})
}).then(r=>r.json()).then(d=>{
window.location="/track/"+d.id
})
}
</script>
""", name=NAME, table=table)

# ---------------- ORDER ----------------
@app.route("/order", methods=["POST"])
def order():
    d = request.json

    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()

    c.execute("INSERT INTO orders VALUES (NULL,?,?,?,?,?,?,?)", (
        d["name"],
        str(d["items"]),
        d["total"],
        d["table"],
        "Confirmar Cliente",
        datetime.now().strftime("%d-%m-%Y %H:%M"),
        d.get("phone","")
    ))

    oid = c.lastrowid
    conn.commit()
    conn.close()

    return jsonify({"id":oid})

# ---------------- TRACK ----------------
@app.route("/track/<int:id>")
def track(id):
    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    o = c.execute("SELECT * FROM orders WHERE id=?", (id,)).fetchone()
    conn.close()

    return render_template_string("""
<style>
body{background:#111;color:white;text-align:center;font-family:Arial}
.btn{padding:20px;font-size:20px;margin:10px;border:none;border-radius:10px;width:80%}
.green{background:#28a745}
.red{background:#dc3545}
</style>

<h1>Pedido</h1>
<h2>{{o[5]}}</h2>

<button class="btn green" onclick="fetch('/confirm_order/{{o[0]}}')">✅ Confirmar</button>
<button class="btn red" onclick="fetch('/reject_order/{{o[0]}}')">❌ Cancelar</button>

<script>
setInterval(()=>location.reload(),4000)
</script>
""", o=o)

# ---------------- LIVE DATA ----------------
@app.route("/orders_json")
def orders_json():
    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    rows = c.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    conn.close()

    return jsonify([
        {"id":o[0],"name":o[1],"items":o[2],"table":o[4],"status":o[5]}
        for o in rows
    ])

# ---------------- KITCHEN ----------------
@app.route("/kitchen")
def kitchen():
    if not session.get("admin"):
        return redirect("/admin")

    return render_template_string("""
<style>
body{background:#000;color:white;font-family:Arial;padding:10px}
.card{background:#1a1a1a;padding:15px;margin:10px;border-radius:12px}
button{width:100%;padding:15px;font-size:18px;margin:5px 0;border:none;border-radius:10px}
.blue{background:#007bff}
.yellow{background:#ffc107;color:black}
.green{background:#28a745}
.orange{background:#ff9800}
.status{font-size:20px;margin:10px 0}
</style>

<h1>🍹 Cozinha</h1>

<div id="orders"></div>

<script>
function color(s){
if(s=="Confirmar Cliente") return "blue"
if(s=="Preparar") return "yellow"
if(s=="Concluir") return "green"
if(s=="Entregar") return "orange"
return ""
}

function load(){
fetch("/orders_json")
.then(r=>r.json())
.then(data=>{
let html=""
data.forEach(o=>{
html+=`
<div class="card">
<h2>Mesa ${o.table}</h2>
<p>${o.name}</p>
<p>${o.items}</p>

<div class="status">${o.status}</div>

<button class="blue" onclick="update(${o.id},'Confirmado pelo Cliente')">Confirmar Cliente</button>
<button class="yellow" onclick="update(${o.id},'Preparar')">Preparar</button>
<button class="green" onclick="update(${o.id},'Concluir')">Concluir</button>
<button class="orange" onclick="update(${o.id},'Entregar')">Entregar</button>

<button onclick="window.open('/send_whatsapp/${o.id}')">📲 WhatsApp</button>
</div>
`
})
document.getElementById("orders").innerHTML=html
})
}

function update(id,status){
fetch("/update_status",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({id:id,status:status})
}).then(load)
}

setInterval(load,3000)
load()
</script>
""")

# ---------------- UPDATE ----------------
@app.route("/update_status", methods=["POST"])
def update_status():
    d=request.json
    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()
    c.execute("UPDATE orders SET status=? WHERE id=?", (d["status"],d["id"]))
    conn.commit()
    conn.close()
    return jsonify(ok=True)

# ---------------- CONFIRM / REJECT ----------------
@app.route("/confirm_order/<int:id>")
def confirm_order(id):
    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()
    c.execute("UPDATE orders SET status='Confirmado pelo Cliente' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return "ok"

@app.route("/reject_order/<int:id>")
def reject_order(id):
    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()
    c.execute("UPDATE orders SET status='Cancelado' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return "ok"

# ---------------- WHATSAPP ----------------
@app.route("/send_whatsapp/<int:id>")
def send_whatsapp(id):
    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    o = c.execute("SELECT * FROM orders WHERE id=?", (id,)).fetchone()
    conn.close()

    phone = o[7] if len(o)>7 else ""

    if not phone:
        return "No phone"

    phone = phone.replace(" ","").replace("+","")
    if not phone.startswith("258"):
        phone = "258"+phone

    msg=f"Mesa {o[4]} - {o[5]}"
    return redirect("https://wa.me/"+phone+"?text="+urllib.parse.quote(msg))

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
