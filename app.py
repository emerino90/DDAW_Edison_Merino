# Semana 12 — Inventario con SQLite:
# CRUD + búsqueda + totales + mensajes flash (sin extras)

from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DecimalField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange

app = Flask(__name__)
app.config["SECRET_KEY"] = "clave_super_secreta_cambia_esto"

# ---------- SQLite ----------
DB_PATH = Path("inventario.db")

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
                cantidad INTEGER NOT NULL CHECK(cantidad>=0),
                precio   REAL NOT NULL CHECK(precio>=0)
            )
        """)
        conn.commit()

# ---------- Formularios ----------
class ProductoForm(FlaskForm):
    nombre   = StringField("Nombre",   validators=[DataRequired(), Length(min=2, max=50)])
    cantidad = IntegerField("Cantidad", validators=[DataRequired(), NumberRange(min=0)])
    precio   = DecimalField("Precio",   places=2, validators=[DataRequired(), NumberRange(min=0)])
    enviar   = SubmitField("Guardar")

class DeleteForm(FlaskForm):
    enviar = SubmitField("Eliminar")

# ---------- Rutas ----------
@app.route("/")
def home():
    # Listado + barra de búsqueda + totales
    q = (request.args.get("q") or "").strip().lower()
    with get_conn() as conn:
        filas = conn.execute("SELECT id,nombre,cantidad,precio FROM productos ORDER BY id").fetchall()
    productos = [p for p in filas if q in p["nombre"].lower()] if q else filas
    total_items = sum(p["cantidad"] for p in productos)
    total_valor = sum(p["cantidad"] * p["precio"] for p in productos)
    return render_template("index.html",
                           productos=productos,
                           delete_form=DeleteForm(),
                           q=q,
                           total_items=total_items,
                           total_valor=total_valor,
                           titulo="Inventario (SQLite)")

@app.route("/nuevo/", methods=["GET","POST"])
def nuevo():
    form = ProductoForm()
    if form.validate_on_submit():
        with get_conn() as conn:
            conn.execute("INSERT INTO productos(nombre,cantidad,precio) VALUES (?,?,?)",
                         (form.nombre.data.strip(),
                          int(form.cantidad.data),
                          float(form.precio.data)))
            conn.commit()
        flash("Producto creado.", "success")
        return redirect(url_for("home"))
    return render_template("product_form.html", form=form, titulo="Nuevo producto")

@app.route("/editar/<int:pid>/", methods=["GET","POST"])
def editar(pid: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM productos WHERE id=?", (pid,)).fetchone()
    if row is None:
        flash("Producto no encontrado.", "warning")
        return redirect(url_for("home"))

    form = ProductoForm()
    if request.method == "GET":
        form.nombre.data = row["nombre"]
        form.cantidad.data = row["cantidad"]
        form.precio.data = row["precio"]

    if form.validate_on_submit():
        with get_conn() as conn:
            conn.execute("UPDATE productos SET nombre=?, cantidad=?, precio=? WHERE id=?",
                         (form.nombre.data.strip(),
                          int(form.cantidad.data),
                          float(form.precio.data),
                          pid))
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
        flash("Solicitud inválida.", "warning")
    return redirect(url_for("home"))

# ---------- Entrada ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
    
# ---------------------- SQLAlchemy (demo usuarios.db) ---------
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

# Carpeta /database y archivo usuarios.db
DB_DIR = (Path(__file__).parent / "database")
DB_DIR.mkdir(exist_ok=True)

ENGINE = create_engine(f"sqlite:///{DB_DIR/'usuarios.db'}", echo=False, future=True)
Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuarios"
    id     = Column(Integer, primary_key=True)
    nombre = Column(String(80), nullable=False)
    email  = Column(String(120), nullable=False)

Base.metadata.create_all(ENGINE)
Session = sessionmaker(bind=ENGINE, expire_on_commit=False)

@app.route("/usuarios/crear")
def usuarios_crear():
    """
    Crea rápidamente un usuario de prueba:
    /usuarios/crear?nombre=Ana&email=ana@mail.com
    Si no mandas parámetros, usa valores demo.
    """
    nombre = (request.args.get("nombre") or "Usuario Demo").strip()
    email  = (request.args.get("email")  or "demo@mail.com").strip()
    with Session() as s:
        s.add(Usuario(nombre=nombre, email=email))
        s.commit()
    return {"ok": True, "mensaje": f"Usuario '{nombre}' creado"}

@app.route("/usuarios/listar")
def usuarios_listar():
    """Lista todos los usuarios de usuarios.db (SQLAlchemy)."""
    with Session() as s:
        users = s.query(Usuario).order_by(Usuario.id).all()
    data = [{"id": u.id, "nombre": u.nombre, "email": u.email} for u in users]
    return {"total": len(data), "usuarios": data}
