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
        <input name="pass" placeholder="Password" type="password"><br><br>
        <button>Login</button>
    </form>
    """)

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
body{background:#0f0f0f;color:#fff;font-family:Arial;padding:20px;font-size:18px}
h1{text-align:center;color:#ff3b3b;font-size:36px}
h2{border-left:6px solid #ff3b3b;padding-left:10px;margin-top:25px}
.card{background:#1c1c1c;padding:15px;margin:12px 0;border-radius:12px;display:flex;justify-content:space-between;align-items:center}
button{background:#ff3b3b;color:#fff;border:none;padding:12px 18px;border-radius:10px;font-size:18px}
input{width:100%;padding:14px;margin-bottom:10px;border-radius:10px;font-size:16px}
.cart-box{position:fixed;bottom:0;left:0;width:100%;background:#000;padding:15px;border-top:2px solid #ff3b3b}
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
</div>

<script>
let cart=[];let total=0;

function add(n,p){
cart.push(n);
total+=p;
document.getElementById("cart").innerHTML+="<li>"+n+"</li>";
document.getElementById("total").innerText=total+" MZN";
alert(n + " adicionado!");
}

function order(){
if(cart.length==0){
alert("Carrinho vazio!");
return;
}

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
alert("Pedido enviado!");
window.location="/track/"+d.id;
});
}
</script>
""", items=items, name=NAME, table=table)

# ---------------- ORDER ----------------
@app.route("/order", methods=["POST"])
def order():
    d = request.json

    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()

    # 🔥 NEW: order starts waiting for customer confirmation
    c.execute("""
        INSERT INTO orders VALUES (NULL,?,?,?,?,?,?,?)
    """, (
        d["name"],
        str(d["items"]),
        d["total"],
        d["table"],
        "Aguardando Confirmação",
        datetime.now().strftime("%d-%m-%Y %H:%M"),
        d.get("phone", "")
    ))

    oid = c.lastrowid
    conn.commit()
    conn.close()

    return jsonify({"id": oid})

# ---------------- TRACK ----------------
@app.route("/track/<int:id>")
def track(id):
    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()
    o=c.execute("SELECT * FROM orders WHERE id=?", (id,)).fetchone()
    conn.close()

    return render_template_string("""
<h1>📦 Pedido</h1>
<p>Status: {{o[5]}}</p>
<script>
setInterval(()=>{
location.reload();
},4000);
</script>
""", o=o)

# ---------------- LIVE DATA ----------------
@app.route("/orders_json")
def orders_json():
    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    rows = c.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    conn.close()

    data=[]
    for o in rows:
        data.append({
            "id":o[0],
            "name":o[1],
            "items":o[2],
            "total":o[3],
            "table":o[4],
            "status":o[5]
        })

    return jsonify(data)

# ---------------- KITCHEN ----------------
":"@app.route("/kitchen")
def kitchen():
    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()

    active=c.execute("SELECT * FROM orders WHERE status!='Concluído' ORDER BY id DESC").fetchall()
    done=c.execute("SELECT * FROM orders WHERE status='Concluído' ORDER BY id DESC LIMIT 20").fetchall()

    conn.close()

    return render_template_string("""
<style>
body{background:#0b0b0b;color:white;font-family:Arial;padding:15px}
h1{text-align:center;color:#ffcc00;font-size:42px}
h2{font-size:28px;margin-top:30px;border-left:6px solid #ff3b3b;padding-left:10px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:15px}
.order{background:#1a1a1a;padding:20px;border-radius:15px;font-size:22px}
.status{padding:10px;border-radius:10px;font-weight:bold;text-align:center}
.pending{background:#ffc107;color:black}
.preparing{background:#17a2b8}
.done{background:#28a745}
.delivering{background:#ff9800;color:black}

button{margin:8px;padding:12px;border:none;border-radius:8px;font-size:18px;cursor:pointer}
.yellow{background:#ffc107}
.green{background:#28a745;color:white}
.red{background:#dc3545;color:white}
.blue{background:#17a2b8;color:white}
.orange{background:#ff9800;color:black}
</style>

<h1>🍹 Bar e Cozinha</h1>

<h2>📌 Ativos</h2>
<div class="grid">
{% for o in active %}
<div class="order">
<b style="font-size:26px;">Mesa {{o[4]}}</b><br>
👤 {{o[1]}}<br><br>
🍽️ {{o[2]}}<br><br>

<div class="status 
{% if o[5]=='Pendente' %}pending{% endif %}
{% if o[5]=='Preparando' %}preparing{% endif %}
{% if o[5]=='Concluído' %}done{% endif %}
{% if o[5]=='Entregando' %}delivering{% endif %}
">
{{o[5]}}
</div>

<button class="yellow" onclick="update({{o[0]}},'Preparando')">Preparar</button>
<button class="green" onclick="update({{o[0]}},'Concluído')">Concluir</button>
<button class="orange" onclick="update({{o[0]}},'Entregando')">🚚 Entregar</button>

<button class="blue" onclick="confirmOrder({{o[0]}})">📲 Confirmar Cliente</button>

<button class="red" onclick="window.open('/receipt_any/{{o[0]}}')">🧾</button>
<button onclick="window.open('/send_whatsapp/{{o[0]}}')">📲 WhatsApp</button>
</div>
{% endfor %}
</div>

<h2>✅ Concluídos</h2>
<div class="grid">
{% for o in done %}
<div class="order">
<b>Mesa {{o[4]}}</b><br>
👤 {{o[1]}}<br><br>
🍽️ {{o[2]}}<br>

<div class="status done">Concluído</div>

<button onclick="window.open('/receipt_any/{{o[0]}}')">🧾</button>
<button onclick="window.open('/send_whatsapp/{{o[0]}}')">📲</button>
</div>
{% endfor %}
</div>

<script>
function update(id,status){

let msg="";
if(status=="Preparando"){msg="Pedido em preparação";}
if(status=="Concluído"){msg="Pedido concluído";}
if(status=="Entregando"){msg="Pedido a caminho da mesa";}

fetch("/update_status",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({id:id,status:status})
}).then(()=>{
alert(msg);
location.reload();
});
}

function confirmOrder(id){
fetch("/confirm_order/"+id).then(()=>{
alert("Cliente notificado");
});
}
</script>
""", active=active, done=done)

# ---------------- CONFIRM ----------------
@app.route("/confirm_order/<int:id>")
def confirm_order(id):
    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()
    c.execute("UPDATE orders SET status='Confirmado pelo Cliente' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return "ok"

# ---------------- SALES ----------------
@app.route("/sales")
def sales():
    if not session.get("admin"):
        return redirect("/admin")

    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()
    rows=c.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    conn.close()

    return render_template_string("""
<h1>📊 Vendas</h1>
{% for o in rows %}
<div>
Mesa {{o[4]}} - {{o[1]}} - {{o[3]}} MZN - {{o[5]}}
</div>
{% endfor %}
""", rows=rows)

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

    phone = phone.strip().replace(" ", "").replace("+", "")

    if not phone.startswith("258"):
        phone = "258" + phone

    msg = f"""
Peri Peri

Mesa {o[4]}
{ o[2] }

Total {o[3]} MZN
Status {o[5]}
"""

    url = "https://wa.me/" + phone + "?text=" + urllib.parse.quote(msg)
    return redirect(url)

# ---------------- CUSTOMER CONFIRM ORDER ----------------
@app.route("/confirm_order/<int:id>")
def confirm_order(id):
    conn = sqlite3.connect("restaurant.db")
    c = conn.cursor()
    c.execute("UPDATE orders SET status='Confirmado pelo Cliente' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return "ok"
# ---------------- RUN ----------------
if __name__=="__main__":
    app.run()
