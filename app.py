# app.py — Semana 11: CRUD SQLite con Flask-WTF, búsqueda, totales y flashes

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DecimalField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange
import sqlite3
from pathlib import Path

app = Flask(__name__)
app.config["SECRET_KEY"] = "cambia_esta_clave_super_secreta"  # necesaria para CSRF/Flask-WTF

# ---------------------- SQLite ----------------------
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "inventario.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS productos(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre   TEXT NOT NULL,
            precio   REAL NOT NULL CHECK(precio >= 0),
            cantidad INTEGER NOT NULL CHECK(cantidad >= 0)
        )
        """)
        conn.commit()

# ---------------------- Formularios -----------------
class ProductoForm(FlaskForm):
    nombre   = StringField("Nombre",   validators=[DataRequired(), Length(min=2, max=80)])
    precio   = DecimalField("Precio",  places=2, validators=[DataRequired(), NumberRange(min=0)])
    cantidad = IntegerField("Cantidad", validators=[DataRequired(), NumberRange(min=0)])
    enviar   = SubmitField("Guardar")

class DeleteForm(FlaskForm):
    enviar = SubmitField("Eliminar")

# ---------------------- Rutas -----------------------
@app.route("/")
def home():
    with get_conn() as conn:
        filas = conn.execute("SELECT id,nombre,precio,cantidad FROM productos ORDER BY id").fetchall()
    total_items = sum(p["cantidad"] for p in filas)
    total_valor = sum(p["cantidad"] * p["precio"] for p in filas)
    return render_template("index.html",
                           productos=filas,
                           total_items=total_items,
                           total_valor=total_valor,
                           delete_form=DeleteForm(),
                           titulo="Inventario (SQLite)")

@app.route("/nuevo/", methods=["GET", "POST"])
def nuevo():
    form = ProductoForm()
    if form.validate_on_submit():
        with get_conn() as conn:
            conn.execute("INSERT INTO productos(nombre, precio, cantidad) VALUES (?,?,?)",
                         (form.nombre.data.strip(), float(form.precio.data), int(form.cantidad.data)))
            conn.commit()
        flash("Producto creado.", "success")
        return redirect(url_for("home"))
    return render_template("product_form.html", form=form, titulo="Nuevo producto")

@app.route("/editar/<int:pid>/", methods=["GET", "POST"])
def editar(pid: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM productos WHERE id=?", (pid,)).fetchone()
    if row is None:
        flash("Producto no encontrado.", "warning")
        return redirect(url_for("home"))

    form = ProductoForm()
    if request.method == "GET":
        form.nombre.data = row["nombre"]
        form.precio.data = row["precio"]
        form.cantidad.data = row["cantidad"]

    if form.validate_on_submit():
        with get_conn() as conn:
            conn.execute("UPDATE productos SET nombre=?, precio=?, cantidad=? WHERE id=?",
                         (form.nombre.data.strip(), float(form.precio.data), int(form.cantidad.data), pid))
            conn.commit()
        flash("Producto actualizado.", "success")
        return redirect(url_for("home"))

    return render_template("product_form.html", form=form, titulo=f"Editar (ID {pid})")

@app.route("/eliminar/<int:pid>/", methods=["POST"])
def eliminar(pid: int):
    form = DeleteForm()
    if form.validate_on_submit():
        with get_conn() as conn:
            conn.execute("DELETE FROM productos WHERE id=?", (pid,))
            conn.commit()
        flash(f"Producto ID {pid} eliminado.", "info")
    else:
        flash("Solicitud inválida.", "danger")
    return redirect(url_for("home"))

@app.route("/buscar")
def buscar():
    q = (request.args.get("q") or "").strip().lower()
    with get_conn() as conn:
        filas = conn.execute("SELECT id,nombre,precio,cantidad FROM productos ORDER BY id").fetchall()
    resultados = [p for p in filas if q in p["nombre"].lower()] if q else []
    total_items = sum(p["cantidad"] for p in resultados)
    total_valor = sum(p["cantidad"] * p["precio"] for p in resultados)
    return render_template("index.html",
                           productos=resultados,
                           total_items=total_items,
                           total_valor=total_valor,
                           q=q,
                           delete_form=DeleteForm(),
                           titulo="Inventario (SQLite)")

# ---------------------- Main ------------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
