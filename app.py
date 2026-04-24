from flask import Flask, request, jsonify, render_template_string
import sqlite3
from datetime import datetime

app = Flask(__name__)

NAME = "Peri Peri 🌶️"

# ---------------- DATABASE ----------------
def connect_db():
    return sqlite3.connect("restaurant.db")

def init_db():
    conn = connect_db()
    c = conn.cursor()

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

# ---------------- CUSTOMER ----------------
@app.route("/")
def menu():
    table = request.args.get("table", "1")

    return render_template_string("""
    <h1>{{name}}</h1>
    <p>Mesa {{table}}</p>

    <input id="name" placeholder="Seu nome">

    <button onclick="order()">Enviar Pedido</button>

    <script>
    function order(){
        fetch("/order",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({
                name: document.getElementById("name").value,
                items:["Pedido teste"],
                total:100,
                table:"{{table}}"
            })
        }).then(res=>res.json())
        .then(d=>{
            window.location="/track/"+d.id;
        });
    }
    </script>
    """, name=NAME, table=table)

# ---------------- CREATE ORDER ----------------
@app.route("/order", methods=["POST"])
def order():
    d = request.json

    conn = connect_db()
    c = conn.cursor()

    c.execute("INSERT INTO orders (name,items,total,table_no,status,datetime) VALUES (?,?,?,?,?,?)",
              (d["name"], str(d["items"]), d["total"], d["table"],
               "Pendente", datetime.now().strftime("%d-%m-%Y %H:%M")))

    oid = c.lastrowid

    conn.commit()
    conn.close()

    return jsonify({"id": oid})

# ---------------- TRACK ----------------
@app.route("/track/<int:id>")
def track(id):
    conn = connect_db()
    c = conn.cursor()
    o = c.execute("SELECT * FROM orders WHERE id=?", (id,)).fetchone()
    conn.close()

    return render_template_string("""
    <meta http-equiv="refresh" content="5">
    <h2>📦 Estado do Pedido</h2>
    <p>Nome: {{o[1]}}</p>
    <p>Mesa: {{o[4]}}</p>
    <p>Status: {{o[5]}}</p>
    <p>Data: {{o[6]}}</p>
    """, o=o)

# ---------------- KITCHEN ----------------
@app.route("/kitchen")
def kitchen():
    conn = connect_db()
    c = conn.cursor()
    orders = c.execute("SELECT * FROM orders WHERE status!='Concluído' ORDER BY id DESC").fetchall()
    conn.close()

    return render_template_string("""
    <meta http-equiv="refresh" content="5">

    <h1>👨‍🍳 Cozinha</h1>

    <audio id="sound" src="https://www.soundjay.com/buttons/sounds/button-3.mp3"></audio>

    {% for o in orders %}
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

    <button onclick="printReceipt({{o[0]}})">🧾 Imprimir</button>

    </div>
    {% endfor %}

    <script>
    let lastCount = 0;

    function checkSound(){
        let current = document.querySelectorAll("div").length;
        if(current > lastCount){
            document.getElementById("sound").play();
        }
        lastCount = current;
    }

    setInterval(checkSound, 3000);

    function update(id,status){
        fetch("/update_status",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({id:id,status:status})
        }).then(()=>location.reload());
    }

    function printReceipt(id){
        window.open("/receipt/"+id,"_blank");
    }
    </script>
    """, orders=orders)

# ---------------- UPDATE ----------------
@app.route("/update_status", methods=["POST"])
def update():
    d = request.json
    conn = connect_db()
    c = conn.cursor()
    c.execute("UPDATE orders SET status=? WHERE id=?", (d["status"], d["id"]))
    conn.commit()
    conn.close()
    return jsonify(ok=True)

# ---------------- RECEIPT (KITCHEN ONLY) ----------------
@app.route("/receipt/<int:id>")
def receipt(id):
    conn = connect_db()
    c = conn.cursor()
    o = c.execute("SELECT * FROM orders WHERE id=?", (id,)).fetchone()
    conn.close()

    return render_template_string("""
    <body onload="window.print()">
    <h2>🧾 Peri Peri 🌶️</h2>
    <p>Nome: {{o[1]}}</p>
    <p>Mesa: {{o[4]}}</p>
    <p>Itens: {{o[2]}}</p>
    <p>Total: {{o[3]}} MZN</p>
    <p>{{o[6]}}</p>
    </body>
    """, o=o)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()
