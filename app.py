from flask import Flask, request, jsonify, render_template_string, redirect, send_file
import sqlite3
from datetime import datetime
import qrcode
from io import BytesIO

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

# ✅ SAFE DB UPGRADE (ADD PHONE COLUMN)
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
<style>
body{background:#0f0f0f;color:#fff;font-family:Arial;padding:15px}
h1{text-align:center;color:#ff3b3b}
h2{border-left:4px solid #ff3b3b;padding-left:10px}
.card{background:#1c1c1c;padding:12px;margin:10px 0;border-radius:12px;display:flex;justify-content:space-between}
button{background:#ff3b3b;color:#fff;border:none;padding:8px;border-radius:8px}
input{width:100%;padding:10px;margin-bottom:10px;border-radius:8px}
</style>

<h1>🌶️ {{name}}</h1>

<p>Mesa {{table}}</p>
<input id="name" placeholder="Seu nome">
<input id="phone" placeholder="WhatsApp (opcional)">

<h2>🍽️ Comida</h2>
{% for i in items if i[3]=='food' %}
<div class="card">
<div>{{i[1]}}<br><small>{{i[2]}} MZN</small></div>
<button onclick="add('{{i[1]}}',{{i[2]}})">+</button>
</div>
{% endfor %}

<h2>🍺 Bebidas</h2>
{% for i in items if i[3]=='drink' %}
<div class="card">
<div>{{i[1]}}<br><small>{{i[2]}} MZN</small></div>
<button onclick="add('{{i[1]}}',{{i[2]}})">+</button>
</div>
{% endfor %}

<h3>🍽️ Bandeja</h3>
<ul id="cart"></ul>
<h3 id="total">0 MZN</h3>

<button style="width:100%;padding:12px" onclick="order()">📦 Enviar Pedido</button>

<script>
let cart=[];let total=0;

function add(n,p){
cart.push(n);
total+=p;
document.getElementById("cart").innerHTML+="<li>"+n+"</li>";
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
              (d["name"],str(d["items"]),d["total"],d["table"],
               "Pendente",datetime.now().strftime("%d-%m-%Y %H:%M"),
               d.get("phone","")))

    oid=c.lastrowid
    conn.commit()
    conn.close()

    return jsonify({"id":oid})

# ---------------- QR GENERATOR ----------------
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

# ---------------- WHATSAPP (UPDATED) ----------------
@app.route("/send_whatsapp/<int:id>")
def send_whatsapp(id):
    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()
    o=c.execute("SELECT * FROM orders WHERE id=?", (id,)).fetchone()
    conn.close()

    phone = ""
    try:
        phone = o[7]
    except:
        pass

    if not phone:
        return jsonify({"msg":"No phone provided"})

    msg=f"""
🧾 Peri Peri

Nome: {o[1]}
Mesa: {o[4]}
Itens: {o[2]}
Total: {o[3]}
Status: {o[5]}
"""

    print("SEND TO:", phone)
    print(msg)

    return jsonify(ok=True)

# ---------------- RUN ----------------
if __name__=="__main__":
    app.run()
