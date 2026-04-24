from flask import Flask, request, jsonify, render_template_string, redirect
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
    <h1>{{name}}</h1>
    <p>Mesa {{table}}</p>

    <input id="name" placeholder="Seu nome">

    <h2>🍽️ Comida</h2>
    {% for i in items if i[3]=='food' %}
    <div>{{i[1]}} - {{i[2]}} MZN
        <button onclick="add('{{i[1]}}',{{i[2]}})">+</button>
    </div>
    {% endfor %}

    <h2>🍺 Bebidas</h2>
    {% for i in items if i[3]=='drink' %}
    <div>{{i[1]}} - {{i[2]}} MZN
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
    <p>Data: {{o[6]}}</p>

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
        <button onclick="window.open('/receipt_any/{{o[0]}}','_blank')">🧾</button>
    </div>
    {% endfor %}

    <h2>✅ Concluídos</h2>

    {% for o in done %}
    <div style="padding:10px;margin:10px;background:lightgreen;">
        <b>Mesa {{o[4]}}</b> | {{o[1]}}<br>
        {{o[2]}}<br>
        ✔ Concluído

        <button onclick="window.open('/receipt_any/{{o[0]}}','_blank')">🧾</button>
    </div>
    {% endfor %}

    <script>
    let lastCount=0;

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

# ---------------- RECEIPT ANYTIME ----------------
@app.route("/receipt_any/<int:id>")
def receipt_any(id):
    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()
    o=c.execute("SELECT * FROM orders WHERE id=?", (id,)).fetchone()
    conn.close()

    return render_template_string("""
    <body onload="window.print()">
    <h2>🧾 Peri Peri 🌶️</h2>

    <p>Nome: {{o[1]}}</p>
    <p>Mesa: {{o[4]}}</p>
    <p>Status: {{o[5]}}</p>
    <p>Itens: {{o[2]}}</p>
    <p>Total: {{o[3]}} MZN</p>
    <p>{{o[6]}}</p>
    </body>
    """, o=o)

# ---------------- ADMIN LOGIN ----------------
@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.method=="POST":
        if request.form["user"]=="admin" and request.form["pw"]=="1234":
            return redirect("/dashboard")
        return "❌ Login errado"

    return """
    <h2>🔐 Admin Login</h2>
    <form method="POST">
        <input name="user" placeholder="User"><br>
        <input name="pw" type="password" placeholder="Password"><br>
        <button type="submit">Login</button>
    </form>
    """

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()
    orders=c.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    conn.close()

    return render_template_string("""
    <h1>📊 Admin Dashboard</h1>

    <a href="/kitchen">🍹 Cozinha</a>

    {% for o in orders %}
    <div style="border:1px solid #000;margin:10px;padding:10px;">
        <b>Mesa {{o[4]}}</b> | {{o[1]}} | {{o[5]}}<br>
        {{o[2]}}<br>
        {{o[6]}}

        <br><br>
        <button onclick="window.open('/receipt_any/{{o[0]}}','_blank')">🧾 Recibo</button>
        <button onclick="sendWA({{o[0]}})">📲 WhatsApp</button>
    </div>
    {% endfor %}

    <script>
    function sendWA(id){
        fetch("/send_whatsapp/"+id)
        .then(()=>alert("Mensagem enviada (modo demo)"))
    }
    </script>
    """, orders=orders)

# ---------------- WHATSAPP (DEMO) ----------------
def send_whatsapp_message(number, message):
    print("WHATSAPP TO:", number)
    print(message)

@app.route("/send_whatsapp/<int:id>")
def send_whatsapp(id):
    conn=sqlite3.connect("restaurant.db")
    c=conn.cursor()
    o=c.execute("SELECT * FROM orders WHERE id=?", (id,)).fetchone()
    conn.close()

    msg=f"""
🧾 Peri Peri Order

Nome: {o[1]}
Mesa: {o[4]}
Itens: {o[2]}
Total: {o[3]} MZN
Status: {o[5]}
Data: {o[6]}
"""

    send_whatsapp_message("+258XXXXXXXXX", msg)

    return jsonify(ok=True)

# ---------------- RUN ----------------
if __name__=="__main__":
    app.run()
