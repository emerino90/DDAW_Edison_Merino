# ==============================================================
# app.py — Semana 10:
# Inventario (SQLite CRUD + búsqueda) + Persistencia TXT/JSON/CSV
# + Importadores TXT/JSON/CSV -> SQLite
# ==============================================================

from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3, json, csv
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = "clave-super-secreta-cambiala"

# ---------------------- SQLITE (productos) ----------------------
DB_PATH = "inventario.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS productos(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            cantidad INTEGER NOT NULL CHECK(cantidad>=0),
            precio REAL NOT NULL CHECK(precio>=0)
        )""")
        conn.commit()

# ---------------------- Helpers numéricos -----------------------
def _as_int(v, default=0):
    try: return int(v)
    except (TypeError, ValueError): return default

def _as_float(v, default=0.0):
    try: return float(str(v).replace(",", "."))
    except (TypeError, ValueError): return default

# ---------------------- Archivos de datos -----------------------
BASE_DIR = Path(__file__).parent
DATOS_DIR = BASE_DIR / "datos"
DATOS_DIR.mkdir(exist_ok=True)

TXT_PATH  = DATOS_DIR / "datos.txt"
JSON_PATH = DATOS_DIR / "datos.json"
CSV_PATH  = DATOS_DIR / "datos.csv"

# ---- TXT
@app.route("/txt/guardar")
def guardar_txt():
    nombre   = (request.args.get("nombre") or "Producto TXT").strip()
    cantidad = _as_int(request.args.get("cantidad"), 1)
    precio   = _as_float(request.args.get("precio"), 1.0)
    fecha    = datetime.now().isoformat(timespec="seconds")
    linea = f"{fecha} | {nombre} | {cantidad} | {precio:.2f}\n"
    with open(TXT_PATH, "a", encoding="utf-8") as f:
        f.write(linea)
    flash("Registrado en datos.txt", "success")
    return redirect(url_for("home"))

@app.route("/txt/ver")
def ver_txt():
    contenido = TXT_PATH.read_text(encoding="utf-8") if TXT_PATH.exists() else "(archivo vacío)"
    return f"<pre>{contenido}</pre>"

# ---- JSON
def _json_load():
    if JSON_PATH.exists():
        try: return json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError: return []
    return []

def _json_save(data):
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

@app.route("/json/guardar")
def guardar_json():
    nombre   = (request.args.get("nombre") or "Producto JSON").strip()
    cantidad = _as_int(request.args.get("cantidad"), 1)
    precio   = _as_float(request.args.get("precio"), 1.0)
    fecha    = datetime.now().isoformat(timespec="seconds")
    data = _json_load()
    data.append({"fecha": fecha, "nombre": nombre, "cantidad": cantidad, "precio": precio})
    _json_save(data)
    flash("Registrado en datos.json", "success")
    return redirect(url_for("home"))

@app.route("/json/ver")
def ver_json():
    data = _json_load()
    return f"<pre>{json.dumps(data, ensure_ascii=False, indent=2)}</pre>"

# ---- CSV
@app.route("/csv/guardar")
def guardar_csv():
    nombre   = (request.args.get("nombre") or "Producto CSV").strip()
    cantidad = _as_int(request.args.get("cantidad"), 1)
    precio   = _as_float(request.args.get("precio"), 1.0)
    fecha    = datetime.now().isoformat(timespec="seconds")

    write_header = not CSV_PATH.exists() or CSV_PATH.stat().st_size == 0
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["fecha", "nombre", "cantidad", "precio"])
        if write_header: w.writeheader()
        w.writerow({"fecha": fecha, "nombre": nombre, "cantidad": cantidad, "precio": f"{precio:.2f}"})
    flash("Registrado en datos.csv", "success")
    return redirect(url_for("home"))

@app.route("/csv/ver")
def ver_csv():
    if not CSV_PATH.exists() or CSV_PATH.stat().st_size == 0:
        return "<pre>(archivo vacío)</pre>"
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return f"<pre>{json.dumps(rows, ensure_ascii=False, indent=2)}</pre>"

# ---- Importadores -> SQLite
def _upsert_producto(nombre: str, cantidad: int, precio: float):
    if not nombre: return 0
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM productos WHERE nombre=?", (nombre,)).fetchone()
        if row:
            conn.execute(
                "UPDATE productos SET cantidad = cantidad + ?, precio = ? WHERE id = ?",
                (max(0, cantidad), max(0.0, precio), row["id"])
            )
        else:
            conn.execute(
                "INSERT INTO productos(nombre, cantidad, precio) VALUES (?,?,?)",
                (nombre, max(0, cantidad), max(0.0, precio))
            )
        conn.commit()
    return 1

@app.route("/import/txt")
def import_txt():
    if not TXT_PATH.exists(): 
        flash("datos.txt no existe", "warning"); return redirect(url_for("home"))
    procesados = 0
    for line in TXT_PATH.read_text(encoding="utf-8").splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 4: continue
        _, nombre, cant, prec = parts
        procesados += _upsert_producto(nombre, _as_int(cant), _as_float(prec))
    flash(f"Importado TXT: {procesados}", "info")
    return redirect(url_for("home"))

@app.route("/import/json")
def import_json():
    if not JSON_PATH.exists():
        flash("datos.json no existe", "warning"); return redirect(url_for("home"))
    try:
        data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        flash("JSON inválido", "danger"); return redirect(url_for("home"))
    procesados = 0
    for obj in data if isinstance(data, list) else []:
        procesados += _upsert_producto(
            (obj.get("nombre") or "").strip(),
            _as_int(obj.get("cantidad")),
            _as_float(obj.get("precio"))
        )
    flash(f"Importado JSON: {procesados}", "info")
    return redirect(url_for("home"))

@app.route("/import/csv")
def import_csv():
    if not CSV_PATH.exists() or CSV_PATH.stat().st_size == 0:
        flash("datos.csv vacío o no existe", "warning"); return redirect(url_for("home"))
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    procesados = 0
    for r in rows:
        procesados += _upsert_producto(
            (r.get("nombre") or "").strip(),
            _as_int(r.get("cantidad")),
            _as_float(r.get("precio"))
        )
    flash(f"Importado CSV: {procesados}", "info")
    return redirect(url_for("home"))

@app.route("/import/all")
def import_all():
    # Ejecuta los 3, aunque alguno no exista
    import_txt(); import_json(); import_csv()
    return redirect(url_for("home"))

# ---------------------- Rutas CRUD (SQLite) --------------------
@app.route("/")
def home():
    q = (request.args.get("q") or "").strip().lower()
    with get_conn() as conn:
        filas = conn.execute("SELECT id,nombre,cantidad,precio FROM productos ORDER BY id").fetchall()
    productos = [p for p in filas if q in p["nombre"].lower()] if q else filas
    total_items = sum(p["cantidad"] for p in productos)
    total_valor = sum(p["cantidad"] * p["precio"] for p in productos)
    return render_template("index.html",
                           productos=productos, total_items=total_items,
                           total_valor=total_valor, q=q, titulo="Inventario")

@app.route("/nuevo/", methods=["GET","POST"])
def nuevo():
    if request.method == "POST":
        nombre   = (request.form.get("nombre") or "").strip()
        cantidad = _as_int(request.form.get("cantidad"))
        precio   = _as_float(request.form.get("precio"))
        if not nombre:
            flash("El nombre es obligatorio", "warning")
            return redirect(url_for("nuevo"))
        with get_conn() as conn:
            conn.execute("INSERT INTO productos(nombre,cantidad,precio) VALUES (?,?,?)",
                         (nombre, cantidad, precio))
            conn.commit()
        flash("Producto creado.", "success")
        return redirect(url_for("home"))
    return render_template("product_form.html", titulo="Nuevo producto")

@app.route("/editar/<int:pid>/", methods=["GET","POST"])
def editar(pid: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM productos WHERE id=?", (pid,)).fetchone()
    if row is None:
        flash("Producto no encontrado.", "warning")
        return redirect(url_for("home"))
    if request.method == "POST":
        nombre   = (request.form.get("nombre") or "").strip()
        cantidad = _as_int(request.form.get("cantidad"))
        precio   = _as_float(request.form.get("precio"))
        with get_conn() as conn:
            conn.execute("UPDATE productos SET nombre=?,cantidad=?,precio=? WHERE id=?",
                         (nombre, cantidad, precio, pid))
            conn.commit()
        flash("Producto actualizado.", "success")
        return redirect(url_for("home"))
    return render_template("product_form.html", titulo=f"Editar (ID {pid})", p=row)

@app.route("/eliminar/<int:pid>/", methods=["POST"])
def eliminar(pid: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM productos WHERE id=?", (pid,))
        conn.commit()
    flash(f"Producto ID {pid} eliminado.", "info")
    return redirect(url_for("home"))

# ---------------------- Main ------------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
