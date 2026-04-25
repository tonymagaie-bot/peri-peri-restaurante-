from flask import Flask, request, jsonify, render_template_string, redirect, send_file
import sqlite3
from datetime import datetime
import qrcode
from io import BytesIO
import urllib.parse

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

# ---------------- TRACK ----------------
@app.route("/track/<int:id>")
def track(id):
    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()
    o=c.execute("SELECT * FROM orders WHERE id=?", (id,)).fetchone()
    conn.close()

    return render_template_string("""
<style>
body{background:#0f0f0f;color:white;text-align:center;font-family:Arial;padding:20px}
.box{background:#1c1c1c;padding:20px;border-radius:12px}
</style>

<h1>📦 Pedido</h1>

<div class="box">
<p><b>Nome:</b> {{o[1]}}</p>
<p><b>Mesa:</b> {{o[4]}}</p>
<p><b>Status:</b> {{o[5]}}</p>
<p><b>Data:</b> {{o[6]}}</p>
</div>

<button onclick="window.location='/?table={{o[4]}}'">⬅ Voltar</button>
""", o=o)

# ---------------- KITCHEN ----------------
@app.route("/kitchen")
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
button{margin:8px;padding:12px;border:none;border-radius:8px;font-size:18px}
.yellow{background:#ffc107}
.green{background:#28a745;color:white}
.red{background:#dc3545;color:white}
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
">
{{o[5]}}
</div>

<button class="yellow" onclick="update({{o[0]}},'Preparando')">Preparar</button>
<button class="green" onclick="update({{o[0]}},'Concluído')">Concluir</button>
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

fetch("/update_status",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({id:id,status:status})
}).then(()=>{
alert(msg);
location.reload();
});
}
</script>
""", active=active, done=done)

# ---------------- UPDATE STATUS ----------------
@app.route("/update_status", methods=["POST"])
def update_status():
    d=request.json
    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()
    c.execute("UPDATE orders SET status=? WHERE id=?", (d["status"],d["id"]))
    conn.commit()
    conn.close()
    return jsonify(ok=True)

# ---------------- RECEIPT ----------------
@app.route("/receipt_any/<int:id>")
def receipt_any(id):
    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()
    o=c.execute("SELECT * FROM orders WHERE id=?", (id,)).fetchone()
    conn.close()

    return render_template_string("""
<body onload="window.print()">
<h2>🌶️ Peri Peri</h2>
<p>Nome: {{o[1]}}</p>
<p>Mesa: {{o[4]}}</p>
<p>Status: {{o[5]}}</p>
<p>Itens: {{o[2]}}</p>
<p>Total: {{o[3]}} MZN</p>
<p>{{o[6]}}</p>
</body>
""", o=o)

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

# ---------------- WHATSAPP ----------------
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

    phone = phone.replace(" ", "").replace("+", "")

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
if __name__=="__main__":
    app.run()
