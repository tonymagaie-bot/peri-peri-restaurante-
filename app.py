from flask import Flask, request, jsonify, render_template_string
import sqlite3
from datetime import datetime

app = Flask(__name__)

NAME = "Peri Peri 🌶️"

# ---------------- STATUS TRANSLATION ----------------
def status_pt(status):
    mapping = {
        "Pendente": "Pendente",
        "Preparando": "Preparando",
        "Concluído": "Concluído"
    }
    return mapping.get(status, status)

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
        body{background:#111;color:#fff;font-family:sans-serif;padding:15px}
        h1{color:#ff4d4d}
        .card{background:#222;padding:10px;margin:8px;border-radius:8px}
        button{background:#ff4d4d;color:#fff;border:none;padding:6px}
        input{padding:5px;margin:5px}
    </style>
    </head>

    <body>
    <h1>{{name}}</h1>
    <p>Mesa {{table}}</p>

    <input id="name" placeholder="Seu nome">

    <h2>🍽️ Comida</h2>
    {% for i in items if i[3]=='food' %}
    <div class="card">
        {{i[1]}} - {{i[2]}} MZN
        <button onclick="add('{{i[1]}}',{{i[2]}})">+</button>
    </div>
    {% endfor %}

    <h2>🍺 Bebidas</h2>
    {% for i in items if i[3]=='drink' %}
    <div class="card">
        {{i[1]}} - {{i[2]}} MZN
        <button onclick="add('{{i[1]}}',{{i[2]}})">+</button>
    </div>
    {% endfor %}

    <h3>Carrinho</h3>
    <ul id="cart"></ul>
    <h3 id="total">0 MZN</h3>

    <button onclick="order()">Enviar Pedido</button>

    <script>
    let cart=[]; let total=0;

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
                items:cart,
                total:total,
                table:"{{table}}"
            })
        })
        .then(res=>res.json())
        .then(d=>{
            window.location="/track/"+d.id;
        });
    }
    </script>
    </body>
    </html>
    """, items=items, name=NAME, table=table)

# ---------------- ORDER ----------------
@app.route("/order", methods=["POST"])
def order():
    d=request.json

    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()

    c.execute("INSERT INTO orders VALUES (NULL,?,?,?,?,?,?)",
              (d["name"],str(d["items"]),d["total"],d["table"],
               "Pendente",datetime.now().strftime("%d-%m-%Y %H:%M")))

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
    <meta http-equiv="refresh" content="5">

    <h2>📦 Estado do Pedido</h2>

    <p>Nome: {{o[1]}}</p>
    <p>Mesa: {{o[4]}}</p>
    <p>Status: {{o[5]}}</p>
    <p>Status PT: {{o[5]}}</p>
    <p>Data: {{o[6]}}</p>

    <br>
    <button onclick="window.location='/?table={{o[4]}}'">⬅ Voltar ao Menu</button>
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
    <meta http-equiv="refresh" content="5">

    <h1>🍹 Bar e Cozinha</h1>

    <audio id="sound" src="https://www.soundjay.com/buttons/sounds/button-3.mp3"></audio>

    <h2>📌 Ativos</h2>

    {% for o in active %}
    <div style="padding:10px;margin:10px;
    background:
    {% if o[5]=='Pendente' %}orange
    {% elif o[5]=='Preparando' %}yellow
    {% else %}lightgreen{% endif %};">

        <b>Mesa {{o[4]}}</b> | {{o[1]}} | {{o[6]}}<br>
        {{o[2]}}<br>
        {{o[5]}}

        <br><br>
        <button onclick="update({{o[0]}},'Preparando')">Preparando</button>
        <button onclick="update({{o[0]}},'Concluído')">Concluído</button>
        <button onclick="printR({{o[0]}})">🧾</button>
    </div>
    {% endfor %}

    <h2>✅ Concluídos</h2>

    {% for o in done %}
    <div style="padding:10px;margin:10px;background:lightgreen;">
        <b>Mesa {{o[4]}}</b> | {{o[1]}}<br>
        {{o[2]}}<br>
        ✔ Concluído
    </div>
    {% endfor %}

    <script>
    let lastCount = 0;

    function check(){
        let current=document.querySelectorAll("div").length;

        if(current>lastCount){
            let audio=document.getElementById("sound");
            audio.currentTime=0;
            audio.play();
        }

        lastCount=current;
    }

    setInterval(check,3000);

    function update(id,status){
        fetch("/update_status",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({id:id,status:status})
        }).then(()=>location.reload());
    }

    function printR(id){
        window.open("/receipt/"+id,"_blank");
    }
    </script>
    """, active=active, done=done)

# ---------------- UPDATE ----------------
@app.route("/update_status", methods=["POST"])
def update():
    d=request.json
    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()
    c.execute("UPDATE orders SET status=? WHERE id=?", (d["status"],d["id"]))
    conn.commit()
    conn.close()
    return jsonify(ok=True)

# ---------------- RECEIPT ----------------
@app.route("/receipt/<int:id>")
def receipt(id):
    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()
    o=c.execute("SELECT * FROM orders WHERE id=?", (id,)).fetchone()
    conn.close()

    return render_template_string("""
    <body onload="window.print()">
    <h2>Peri Peri 🌶️</h2>
    <p>Nome: {{o[1]}}</p>
    <p>Mesa: {{o[4]}}</p>
    <p>Itens: {{o[2]}}</p>
    <p>Total: {{o[3]}} MZN</p>
    <p>{{o[6]}}</p>
    </body>
    """, o=o)

# ---------------- RUN ----------------
if __name__=="__main__":
    app.run()
