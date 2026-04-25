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
body{
    background:#0a0a0a;
    color:#fff;
    font-family:system-ui;
    padding:18px;
    font-size:20px;
}

h1{
    text-align:center;
    color:#ff4d4d;
    font-size:42px;
    margin-bottom:10px;
}

h2{
    border-left:6px solid #ff4d4d;
    padding-left:12px;
    margin-top:30px;
    font-size:28px;
}

input{
    width:100%;
    padding:18px;
    margin-bottom:12px;
    border-radius:12px;
    border:none;
    font-size:18px;
    background:#1c1c1c;
    color:#fff;
}

.card{
    background:#161616;
    padding:20px;
    margin:14px 0;
    border-radius:16px;
    display:flex;
    justify-content:space-between;
    align-items:center;
    box-shadow:0 4px 15px rgba(0,0,0,0.5);
}

.card div{
    font-size:22px;
}

.card small{
    font-size:16px;
    color:#aaa;
}

button{
    background:#ff4d4d;
    color:#fff;
    border:none;
    padding:14px 22px;
    border-radius:12px;
    font-size:18px;
    font-weight:bold;
}

button:active{
    transform:scale(0.96);
}

.cart-box{
    position:fixed;
    bottom:0;
    left:0;
    width:100%;
    background:#111;
    padding:18px;
    border-top:3px solid #ff4d4d;
}

.cart-box h3{
    margin:5px 0;
}

#cart li{
    font-size:18px;
}

#total{
    font-size:26px;
    color:#00ff88;
}

.cart-box button{
    width:100%;
    font-size:20px;
    margin-top:10px;
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
    margin-bottom:20px;
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
    box-shadow:0 6px 20px rgba(0,0,0,0.6);
}

.order b{
    font-size:28px;
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
<script>
setInterval(()=>location.reload(), 5000);
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
