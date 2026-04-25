from flask import Flask, request, jsonify, render_template_string, redirect, send_file, session
import sqlite3
from datetime import datetime
import qrcode
from io import BytesIO
import urllib.parse

app = Flask(__name__)

# 🔐 ADMIN CONFIG
app.secret_key = "supersecret123"
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

    if c.execute("SELECT COUNT(*) FROM menu").fetchone()[0] == 0:
        items = [
            ("Frango Peri Peri", 400, "food"),
            ("Asas Picantes", 300, "food"),
            ("Hambúrguer", 250, "food"),
            ("Cerveja", 120, "drink"),
            ("Vinho", 250, "drink"),
            ("Whisky", 180, "drink")
        ]
        c.executemany("INSERT INTO menu VALUES (NULL,?,?,?)", items)

    conn.commit()
    conn.close()

init_db()

# ---------------- PHONE COLUMN ----------------
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

# ---------------- ADMIN LOGIN ----------------
@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.method == "POST":
        u = request.form.get("user")
        p = request.form.get("pass")

        if u == ADMIN_USER and p == ADMIN_PASS:
            session["admin"] = True
            return redirect("/kitchen")

    return render_template_string("""
    <h2>🔐 Admin Login</h2>
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

    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    items = c.execute("SELECT * FROM menu").fetchall()
    conn.close()

    return render_template_string("""
<h1>🌶️ {{name}}</h1>
<p>Mesa {{table}}</p>

<input id="name" placeholder="Nome">
<input id="phone" placeholder="WhatsApp">

<h2>Menu</h2>

{% for i in items %}
<div>
{{i[1]}} - {{i[2]}} MZN
<button onclick="add('{{i[1]}}',{{i[2]}})">+</button>
</div>
{% endfor %}

<h3 id="total">0</h3>
<button onclick="order()">Enviar</button>

<script>
let cart=[]
let total=0

function add(n,p){
cart.push(n)
total+=p
document.getElementById("total").innerText=total
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
window.location="/track/"+d.id
})
}
</script>
""", items=items, name=NAME, table=table)

# ---------------- ORDER ----------------
@app.route("/order", methods=["POST"])
def order():
    d = request.json

    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()

    c.execute("""
        INSERT INTO orders VALUES (NULL,?,?,?,?,?,?,?)
    """, (
        d["name"],
        str(d["items"]),
        d["total"],
        d["table"],
        "Aguardando Confirmação do Cliente",
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
<h1>Pedido</h1>

<p>Status: {{o[5]}}</p>

<a href="/confirm_order/{{o[0]}}">✅ Confirmar</a>
<a href="/reject_order/{{o[0]}}">❌ Rejeitar</a>

<script>
setInterval(()=>location.reload(),4000)
</script>
""", o=o)

# ---------------- CUSTOMER CONFIRM ----------------
@app.route("/confirm_order/<int:id>")
def confirm_order(id):
    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    c.execute("UPDATE orders SET status='Confirmado pelo Cliente' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return "OK"

# ---------------- CUSTOMER REJECT ----------------
@app.route("/reject_order/<int:id>")
def reject_order(id):
    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    c.execute("UPDATE orders SET status='Rejeitado pelo Cliente' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return "OK"

# ---------------- LIVE DATA ----------------
@app.route("/orders_json")
def orders_json():
    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    rows = c.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    conn.close()

    return jsonify([
        {
            "id":o[0],
            "name":o[1],
            "items":o[2],
            "total":o[3],
            "table":o[4],
            "status":o[5]
        } for o in rows
    ])

# ---------------- KITCHEN LIVE ----------------
@app.route("/kitchen")
def kitchen():
    if not session.get("admin"):
        return redirect("/admin")

    return render_template_string("""
<h1>🍹 Kitchen Live</h1>

<div id="orders"></div>

<script>
async function load(){
let res = await fetch("/orders_json")
let data = await res.json()

let html = ""

data.forEach(o=>{
html += `
<div style="border:1px solid #fff;margin:10px;padding:10px">
Mesa ${o.table}<br>
${o.name}<br>
${o.items}<br>
Status: ${o.status}<br>

<button onclick="update(${o.id},'Preparando')">Preparar</button>
<button onclick="update(${o.id},'Entregando')">Entregar</button>
<button onclick="update(${o.id},'Concluído')">Concluir</button>
<button onclick="confirm(${o.id})">Confirmar Cliente</button>
</div>
`
})

document.getElementById("orders").innerHTML = html
}

function update(id,status){
fetch("/update_status",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({id:id,status:status})
}).then(load)
}

function confirm(id){
fetch("/confirm_order/"+id).then(load)
}

setInterval(load,3000)
load()
</script>
""")

# ---------------- UPDATE STATUS ----------------
@app.route("/update_status", methods=["POST"])
def update_status():
    d = request.json
    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    c.execute("UPDATE orders SET status=? WHERE id=?", (d["status"],d["id"]))
    conn.commit()
    conn.close()
    return jsonify(ok=True)

# ---------------- WHATSAPP ----------------
@app.route("/send_whatsapp/<int:id>")
def send_whatsapp(id):
    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    o = c.execute("SELECT * FROM orders WHERE id=?", (id,)).fetchone()
    conn.close()

    phone = o[7] if len(o) > 7 else ""

    if not phone:
        return "No phone"

    phone = phone.replace(" ","").replace("+","")

    if not phone.startswith("258"):
        phone = "258" + phone

    msg = f"""
Peri Peri 🌶️
Mesa {o[4]}
{o[2]}
Total {o[3]} MZN
Status {o[5]}
"""

    url = "https://wa.me/"+phone+"?text="+urllib.parse.quote(msg)
    return redirect(url)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
